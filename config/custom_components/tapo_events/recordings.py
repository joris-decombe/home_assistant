"""Copy each hub camera's detection clips to /media, with a thumbnail each.

Layout: /media/tapo/<camera>/<YYYY-MM-DD>/<HH-MM-SS> <kind>.mp4, which HA's
Media panel browses as is, and .thumbs/<same name>.jpg next to it (hidden from
the Media panel). Local copies older than RETENTION_DAYS are deleted; the hub's
own recordings are never touched.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
import logging
from pathlib import Path
import re
import shutil
import time
from typing import TYPE_CHECKING

import aiofiles
from homeassistant.core import HomeAssistant
from pytapo.media_stream import downloader as tapo_downloader  # from Tapo Control

from .const import FRESH_SECONDS, MEDIA_ROOT, RETENTION_DAYS

if TYPE_CHECKING:
    from . import Camera

_LOGGER = logging.getLogger(__name__)

DONE = ("Converting", "Converting [shorter]")
MAX_TRIES = 3  # per clip, until HA restarts


class _Convert(tapo_downloader.Convert):
    """pytapo's raw save drops the audio, which arrives as separate G.711.

    Keep it in a side file named after its format and rate, for ffmpeg to mux
    in later. Only raw saves change, and only this integration asks for those.
    """

    async def save(self, fileLocation, fileLength, method="ffmpeg"):
        await super().save(fileLocation, fileLength, method)
        if method == "raw" and (audio := self.audioWriter.getvalue()):
            side = f"{fileLocation}.{self._get_audio_format()}{self._get_audio_rate()}"
            async with aiofiles.open(side, "wb") as file:
                await file.write(audio)


tapo_downloader.Convert = _Convert


async def _ffmpeg(*args: str) -> bool:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode:
        _LOGGER.debug("ffmpeg %s failed: %s", args, err.decode(errors="replace"))
    return proc.returncode == 0


class Recorder:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._running: set[str] = set()
        self._backfilled: set[str] = set()
        self._failed: dict[tuple[str, int], int] = {}  # (camera, start) -> tries

    def _dir(self, cam: Camera) -> Path:
        return Path(MEDIA_ROOT) / cam.name

    async def load_latest(self, cam: Camera) -> None:
        """Show the newest clip already on disk until a new one comes in."""

        def newest():
            thumbs = sorted(self._dir(cam).glob("*/.thumbs/*.jpg"))
            return (thumbs[-1], thumbs[-1].read_bytes()) if thumbs else (None, None)

        thumb, image = await self.hass.async_add_executor_job(newest)
        if thumb:
            self._show(cam, thumb, image)

    def _show(self, cam: Camera, thumb: Path, image: bytes) -> None:
        day = thumb.parent.parent.name
        cam.image = image
        cam.image_time = datetime.strptime(
            f"{day} {thumb.stem[:8]}", "%Y-%m-%d %H-%M-%S"
        ).astimezone()
        cam.clip = str(thumb.parent.parent / f"{thumb.stem}.mp4")

    async def sync(self, cam: Camera, controller) -> bool:
        """Download missing clips. Returns True if the latest image changed."""
        if cam.dev_id in self._running:
            return False
        self._running.add(cam.dev_id)
        try:
            return await self._sync(cam, controller)
        except Exception as err:  # pytapo raises bare Exceptions
            _LOGGER.warning("Recording sync for %s failed: %s", cam.name, err)
            cam.sync_wanted = True
            return False
        finally:
            self._running.discard(cam.dev_id)

    async def _sync(self, cam: Camera, controller) -> bool:
        job = self.hass.async_add_executor_job
        offset = await job(controller.getTimeCorrection)
        today = date.today()
        # The first run backfills the retention window, later runs the last two days.
        span = 2 if cam.dev_id in self._backfilled else RETENTION_DAYS
        if cam.dev_id not in self._backfilled:  # leftovers of interrupted downloads
            await job(self._clear_partial, cam)
        changed = False
        for back in range(span):
            day = today - timedelta(days=back)
            recordings = await job(controller.getRecordings, day.strftime("%Y%m%d"))
            # video_type "1" is a timed recording; anything else is a detection.
            clips = sorted(
                (int(r["startTime"]), int(r["endTime"]))
                for item in recordings
                for r in item.values()
                if str(r["video_type"]) != "1"
            )
            if not clips:
                continue
            kinds = await self._kinds(controller, clips, offset)
            for start, end in reversed(clips):
                local = datetime.fromtimestamp(start + offset)
                if (local.date() - today).days < -RETENTION_DAYS + 1:
                    continue
                folder = self._dir(cam) / local.strftime("%Y-%m-%d")
                name = f"{local:%H-%M-%S} {kinds.get(start, 'motion')}"
                if (folder / f"{name}.mp4").exists():
                    continue
                if end + offset > time.time() - FRESH_SECONDS:
                    cam.sync_wanted = True  # still being written to the hub
                    continue
                if self._failed.get((cam.dev_id, start), 0) >= MAX_TRIES:
                    continue
                if await self._download(controller, start, end, offset, folder, name):
                    if cam.image_time is None or local.astimezone() >= cam.image_time:
                        thumb = folder / ".thumbs" / f"{name}.jpg"
                        if thumb.exists():
                            self._show(cam, thumb, await job(thumb.read_bytes))
                            changed = True
                else:
                    key = (cam.dev_id, start)
                    self._failed[key] = self._failed.get(key, 0) + 1
                    if self._failed[key] == MAX_TRIES:
                        _LOGGER.warning("Giving up on %s clip %s", cam.name, name)
                    cam.sync_wanted = True
        self._backfilled.add(cam.dev_id)
        await job(self._cleanup, cam)
        return changed

    async def _kinds(self, controller, clips, offset) -> dict[int, str]:
        """Map clip start times to the detection that triggered them."""
        from . import decode

        events = await self.hass.async_add_executor_job(
            controller.getEvents, clips[0][0] - 60, clips[-1][1] + 60
        )
        kinds = {}
        for start, _ in clips:
            for event in events:
                # getEvents returns local times; clips are in the camera's clock.
                if abs(int(event["start_time"]) - offset - start) <= 5:
                    kinds[start] = decode(event)[0]
                    break
        return kinds

    async def _download(self, controller, start, end, offset, folder, name) -> bool:
        partial = folder / ".partial"
        thumbs = folder / ".thumbs"
        await self.hass.async_add_executor_job(
            lambda: [p.mkdir(parents=True, exist_ok=True) for p in (partial, thumbs)]
        )
        ts = partial / f"{name}.ts"
        mp4 = folder / f"{name}.mp4"
        debug = _LOGGER.isEnabledFor(logging.DEBUG)
        if debug:  # pytapo logs through a callback; borrow it for this download
            saved = controller.logger.printDebugInformation
            controller.logger.printDebugInformation = lambda m: _LOGGER.debug(
                "pytapo: %s", m
            )
        try:
            # The H200 ends the fast "download" request with no data for its
            # cameras, so use realtime "playback". Raw MPEG-TS, because pytapo's
            # mp4 conversion runs ffmpeg on the event loop.
            downloader = tapo_downloader.Downloader(
                controller, start, end, offset, f"{partial}/", 0,
                fileName=ts.name, output="ts", method="playback",
            )
            actions = []
            async for status in downloader.download():
                if not actions or actions[-1] != status["currentAction"]:
                    actions.append(status["currentAction"])
        finally:
            if debug:
                controller.logger.printDebugInformation = saved
        audio = await self.hass.async_add_executor_job(
            lambda: next(partial.glob(f"{ts.name}.*law*"), None)
        )
        if not actions or actions[-1] not in DONE or not ts.exists():
            _LOGGER.debug("Download of %s/%s: %s", folder.name, name, actions)
            await self.hass.async_add_executor_job(self._remove, ts, audio)
            return False
        tmp = partial / f"{name}.mp4"
        inputs = ["-i", str(ts)]
        if audio:  # e.g. "<name>.ts.alaw8000"
            fmt, rate = re.fullmatch(r"\.([a-z]+)(\d+)", audio.suffix).groups()
            inputs += ["-f", fmt, "-ar", rate, "-i", str(audio), "-map", "0:v", "-map", "1:a"]
        ok = await _ffmpeg(
            *inputs, "-c:v", "copy", "-c:a", "aac", "-shortest",
            "-movflags", "+faststart", str(tmp),
        )
        await self.hass.async_add_executor_job(self._remove, ts, audio)
        if not ok:
            await self.hass.async_add_executor_job(self._remove, tmp)
            return False
        await self.hass.async_add_executor_job(tmp.replace, mp4)
        _LOGGER.debug("Saved %s", mp4)
        # A frame 2 s in, or the first one for very short clips. A clip
        # without a thumbnail still counts.
        thumb = str(thumbs / f"{name}.jpg")
        frame = ["-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "4", thumb]
        if not await _ffmpeg("-ss", "2", "-i", str(mp4), *frame):
            await _ffmpeg("-i", str(mp4), *frame)
        return True

    def _clear_partial(self, cam: Camera) -> None:
        for path in self._dir(cam).glob("*/.partial/*"):
            path.unlink(missing_ok=True)

    @staticmethod
    def _remove(*paths) -> None:
        for path in paths:
            if path:
                path.unlink(missing_ok=True)

    def _cleanup(self, cam: Camera) -> None:
        oldest = date.today() - timedelta(days=RETENTION_DAYS - 1)
        for day in self._dir(cam).iterdir():
            try:
                old = datetime.strptime(day.name, "%Y-%m-%d").date() < oldest
            except ValueError:
                continue
            if old:
                _LOGGER.debug("Removing %s", day)
                shutil.rmtree(day, ignore_errors=True)
