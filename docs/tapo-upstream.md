# Tapo upstream drafts (not posted)

Drafts for reporting what we found with the H200 hub cameras to
[Tapo Control](https://github.com/JurajNyiri/HomeAssistant-Tapo-Control) and
[pytapo](https://github.com/JurajNyiri/pytapo), so `tapo_events` (see
`docs/tapo-cameras.md`) can eventually go. **Nothing here has been posted, and
no fork or branch exists.**

Setup the findings come from (2026-10-17):

| | |
|---|---|
| Cameras | 2× C420 1.0, firmware 1.4.2 Build 20251226 rel.78318, battery |
| Hubs | 2× H200 1.0, firmware 1.7.7 Build 20260917 rel.79232, one camera each, recording to the hub's microSD |
| Software | Tapo Control 7.2.8, pytapo 3.4.26, Home Assistant 2026.10.1 (HAOS on a Raspberry Pi 3) |
| Added as | hubs added to Tapo Control; the cameras come in as hub children (`controlChild`) |

## Before posting anything

Both repos are maintained by JurajNyiri, and Tapo Control's
[CONTRIBUTING.md](https://github.com/JurajNyiri/HomeAssistant-Tapo-Control/blob/main/CONTRIBUTING.md)
is strict about AI-assisted issues and PRs:

- You're the author. Read every draft, cut anything you can't explain or
  verify yourself, and be ready to answer questions without the AI.
- The bug report template asks you to confirm the LLM usage terms and requires
  a **full debug log** attached (Settings → Integrations → Tapo Control →
  Enable debug logging, reproduce, download the full log). Check the log for
  your password, tokens and public IP before attaching.
- PRs need the AI disclosure block (included below) and must say what was and
  wasn't tested in Home Assistant.
- CONTRIBUTING also asks a coding agent to get your explicit agreement, in the
  conversation, that you'll review and take responsibility for AI-assisted
  changes before it edits the repo, commits, pushes or opens a PR. That's why
  the patches below are diffs only. Say so if you agree and want the forks
  and branches made.

Fill in the `TODO` bits from your own observations first. Battery levels
were 63 % (Front Door) and 49 % (Garage) on 2026-10-17, so compare after a
week of `tapo_events` polling before claiming anything about battery life.

## What goes where

| # | Finding | Where | Form |
|---|---|---|---|
| 1 | `getEvents` (`searchDetectionList`) gives motion/person/vehicle for hub children, fast and local | Tapo Control [#273](https://github.com/JurajNyiri/HomeAssistant-Tapo-Control/issues/273) (open: motion on battery cameras) | Comment |
| 2 | `getRecordingsList` (`searchDateWithVideo`) never answers, so media sync and the Recordings browser never work | Tapo Control | Bug report |
| 3 | Downloader's `download` request ends with no data for hub children; `playback` works | pytapo | Issue + PR A |
| 4 | `getRecordingSnapshot` (media_type 2) gets no answer for hub children | pytapo | Same issue as 3 |
| 5 | `output="ts"` (raw save) drops the G.711 audio | pytapo | PR B (no issue needed) |

Related: [#1445](https://github.com/JurajNyiri/HomeAssistant-Tapo-Control/issues/1445)
(same event codes on a C410, auto-closed for not using the template),
[#1460](https://github.com/JurajNyiri/HomeAssistant-Tapo-Control/issues/1460)
(H200 recordings, same hub firmware), [#1456](https://github.com/JurajNyiri/HomeAssistant-Tapo-Control/issues/1456)
(media scan stuck on the same 10 s read timeout, non-hub camera),
[pytapo#194](https://github.com/JurajNyiri/pytapo/issues/194) (H200 hub
downloads on firmware 1.6.x).

---

## 1. Comment on Tapo Control #273

> Data point for battery cameras behind an H200 hub, since the concerns above
> were polling, battery and consistency.
>
> Setup: two C420 (1.4.2) each paired to an H200 (1.7.7 Build 20260917),
> recording to the hub's SD card, added through the hub in Tapo Control 7.2.8
> (pytapo 3.4.26).
>
> `getEvents()` on the child controller (`searchDetectionList`) answers in
> 0.2–0.3 s, while the camera is asleep. That's too fast for a wake-up, so it
> looks like the hub answers from its own timeline, not the camera. Each event
> has `start_time`, `end_time`, `alarm_type` and `events_1`. The codes match
> #1445:
>
> - `alarm_type`: 2 motion, 6 person, 8 vehicle
> - `events_1` is a bitmask: 2 motion, 32 person, 128 vehicle. Seen here: 2,
>   32, 34, 130, 162.
>
> I've been polling it every 10 s (last 10 minutes each time) from a small
> custom integration that reuses Tapo Control's hub connections, with an event
> entity and motion/person/vehicle binary sensors.
> TODO: events show up N–M s after they start; battery over D days went from
> X % to Y %, same as before / lower.
>
> Tapo Control already calls `searchDetectionList` for its thumbnail preload,
> so an opt-in, hub-children-only motion/person/vehicle sensor fed by this
> poll might be a cheap addition. Happy to test it.

Notes for you: "doesn't wake the camera" is an inference from the timing, not
measured. Only keep it if the battery numbers back it up.

## 2. Tapo Control bug report: media sync never works for H200 cameras

Use the Bug Report form. Field by field:

**Description**

> For cameras added through an H200 hub, media sync and the "Tapo:
> Recordings" browser never show anything. The scan starts with
> `getRecordingsList()` (`searchDateWithVideo`), which the H200 never answers:
> it fails with a read timeout every time, and the scan retries at the media
> polling interval forever. Per-day listing works on the same cameras:
> `getRecordings(date)` (which uses `searchVideoWithUTC` for child devices)
> answers in about 0.2 s with the day's recordings.

**Reproduction Steps**

> 1. Pair a battery camera (C420 here) to an H200 recording to its SD card.
> 2. Add the hub to Tapo Control, enable media sync for the child camera.
> 3. Open Media → Tapo: Recordings, or wait for the media scan.
> 4. The log shows "Unable to retrieve recordings list, will retry at the
>    media polling interval…" and nothing appears.

**Expected behavior**

> Recordings listed and synced, as for directly connected cameras.

**Error logs**

> ```
> getRecordingsList: ReadTimeout: HTTPSConnectionPool(host='<hub IP>', port=443): Read timed out. (read timeout=10)
> ```
> (after 26 s, from a test script calling pytapo directly). TODO: replace
> with the lines from your own debug log.

**Device Firmware**: `H200 1.7.7 Build 20260917 rel.79232; C420 1.4.2 Build 20251226 rel.78318`
**Integration Version**: `7.2.8`
**Last known working integration version**: `Never worked for hub cameras`
**Using stream component**: `No`
**Does camera work via official integrations?**: `N/A` (core TP-Link has no recordings)
**HASS Environment**: `Home Assistant OS on a Raspberry Pi 3`
**Search for similar issues**: `Yes`
**LLM Usage**: your call, after you've reviewed it.

**Additional information**

> A possible fix for child devices: skip `searchDateWithVideo` and walk the
> last N days with `getRecordings()`, or list a date range in one
> `searchVideoWithUTC` call (I haven't tested whether the H200 accepts a
> multi-day range). Related: #1460 (same hub firmware), #1456 (same timeout on
> a non-hub camera).
>
> Downloading these recordings also needs the `playback` request on this hub
> (see pytapo#TODO).

## 3 + 4. pytapo issue: media-port `download` requests get nothing on H200 children

pytapo has no issue template. Keep it short:

> **Title:** H200 hub children: `download` request and recording snapshots
> return no data (playback works)
>
> C420 (1.4.2) behind an H200 (1.7.7 Build 20260917), pytapo 3.4.26, child
> controller (`childID` set), recordings on the hub's SD card.
>
> 1. `Downloader(..., method="download")` (the default): the
>    media session accepts the request, then the stream ends ("Received end of
>    stream.") with no `video/mp2t` data and no error code. The retry does the
>    same, and it ends in "Giving up" after about 20 s. The unsupported-request
>    fallback never runs because there's no error code. The same clip with
>    `method="playback"` downloads fine (H.264 2560×1440, 15 fps).
> 2. `getRecordingSnapshot(tapo, start_time)` for detection recordings
>    (video_type ≠ "1") returns `None` after the 8 s timeout, for each
>    recording tried on both cameras.
>
> Both are the `{"download": {...}}` request shape (media_type 0 and 2); the
> `playback` request works on the same session. I haven't tested whether a
> preceding playback "primes" the hub the way #194 describes for 1.6.x.
>
> PR A falls back to playback when `download` ends with no data. Note that
> Tapo Control's thumbnail preload uses `getRecordingSnapshots`, so on these
> hubs each recording costs a timeout.

TODO before posting: try `method="download"` once right after a successful
playback of the same clip, and say whether it worked.

## PR A (pytapo): fall back to playback when `download` sends nothing

Diff: [`tapo-upstream/pytapo-download-fallback.diff`](tapo-upstream/pytapo-download-fallback.diff),
against pytapo `main` at `17209dd` (3.4.27). Adds 8 lines to `Downloader.download()`:
if a `download` request ends without any video data and without an error
code, switch to `playback`, as already happens when the camera refuses the
request. It also adds a test with a fake session that accepts the request and
then ends, and a README sentence.

Locally: the new test fails on unpatched `main` and passes with the patch.
The other downloader, convert and snapshot tests still pass. Not tested yet:
the patched library against the real hubs (our integration passes
`method="playback"` itself).

Side effect to mention: a directly connected camera that stalls before sending
anything now retries with `playback` instead of `download`.

> **Title:** Downloader: fall back to playback when the download request ends with no data
>
> Cameras behind an H200 hub (1.7.7) accept the `download` request, then end
> the stream without data or an error code, so the existing fallback (which
> waits for an error code) never runs and the download gives up. They answer
> `playback` fine. This treats "no video data at all" like a refused request.
>
> Fixes #TODO (the issue above).
>
> Tested: `pytest test_pytapo.py -k "downloader or convert or snapshot"` (new
> test fails without the change); TODO: download from both H200 cameras with
> the default method.
> Not tested: other hub models, directly connected cameras that stall early.
>
> ```text
> AI assistance: yes
> Tool(s): Claude Code (Claude Opus 5.5)
> AI contribution level: majority of PR
> AI contribution: found the failure in debug logs, wrote the change, test and description
> Human review: TODO
> Home Assistant testing with user: TODO
> ```

## PR B (pytapo): keep the audio of raw (`output="ts"`) saves

Diff: [`tapo-upstream/pytapo-raw-audio.diff`](tapo-upstream/pytapo-raw-audio.diff),
also against `17209dd`.

The camera's G.711 comes in the MPEG-TS under Tapo's private stream types
(0x90/0x91: pytapo's `PES` only extracts audio for those), which ffmpeg doesn't
read. ffprobe on our raw `.ts` clips showed only the H.264 stream, with "record
audio" on. pytapo does decode the G.711 into `Convert.audioWriter`, but
`save(method="raw")` drops it. The patch writes it next to the clip as a Sun
`.au` file (24-byte header with encoding and rate, then the samples):
`clip.ts` → `clip.au`. ffmpeg reads it as `pcm_alaw` / `pcm_mulaw` at the right
rate, and `ffmpeg -i clip.ts -i clip.au -map 0:v -map 1:a -c:v copy -c:a aac
clip.mp4` gives H.264 + AAC (checked with a synthetic clip). It also fixes the
README, which says the raw file has audio.

`tapo_events` does the same with a subclass today (a `.alaw8000` side file);
with this merged it could drop the subclass.

> **Title:** Keep the G.711 audio when saving raw MPEG-TS
>
> With `output="ts"`, the audio is lost: Tapo cameras put G.711 in private
> stream types 0x90/0x91 that ffmpeg doesn't read, and the decoded audio in
> `Convert.audioWriter` isn't saved. This writes it as `<clip>.au` (Sun audio:
> encoding and sample rate in a 24-byte header), which ffmpeg muxes as is.
> No change for `output="mp4"`.
>
> Tested: new `test_convert_save_raw_keeps_audio`, existing raw-save test
> extended; ffprobe/ffmpeg on a generated `.au`. TODO: a real C420 clip.
> Not tested: PCMU (16 kHz) cameras.
>
> ```text
> AI assistance: yes
> Tool(s): Claude Code (Claude Opus 5.5)
> AI contribution level: majority of PR
> AI contribution: diagnosis, change, tests and description
> Human review: TODO
> Home Assistant testing with user: TODO
> ```

### Applying the diffs later

```bash
git clone https://github.com/<you>/pytapo && cd pytapo
git checkout -b download-fallback
git apply ../home_assistant/docs/tapo-upstream/pytapo-download-fallback.diff
```

Both diffs touch `README.md` and `test_pytapo.py` in different places and
apply independently. Rebase on pytapo `main` first if it has moved past
`17209dd`.
