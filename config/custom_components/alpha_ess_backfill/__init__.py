"""Fill gaps in Alpha ESS's hourly statistics from the Alpha ESS cloud.

When HA misses hours (internet down, HA restarting, the Alpha ESS entry
stuck), the energy of those hours lands in the first hour it has data again.
The inverter keeps recording and uploads its readings once it is back
online, so the cloud's getOneDayPowerBySn holds the real shape of those
hours. The service alpha_ess_backfill.run finds such gaps in the last
`hours` and fills them (see gaps.py). An hourly automation in
packages/alpha_ess.yaml calls it. It uses the Alpha ESS integration's own
AppID and secret, so it has no credentials of its own.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta

import aiohttp
import voluptuous as vol

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_metadata,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from . import gaps

_LOGGER = logging.getLogger(__name__)

DOMAIN = "alpha_ess_backfill"
API = "https://openapi.alphaess.com/api/"
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Any(None, {})}, extra=vol.ALLOW_EXTRA)

# Energy statistics: the cloud flow that shapes them, and whether HA's
# catch-up may be overridden by the cloud's energy (see gaps.fill_sum).
SUMS = {
    "sensor.alphaess_solar_production": ("pv", True),
    "sensor.alphaess_daily_pv_generation": ("pv", True),
    "sensor.alphaess_today_s_generation": ("pv", True),
    "sensor.alphaess_total_generation": ("pv", False),
    "sensor.alphaess_grid_to_load": ("import", True),
    "sensor.alphaess_daily_grid_consumption": ("import", True),
    "sensor.alphaess_solar_to_grid": ("export", False),
    "sensor.alphaess_daily_feed_in": ("export", False),
    "sensor.alphaess_charge": ("charge", True),
    "sensor.alphaess_daily_battery_charge": ("charge", True),
    "sensor.alphaess_discharge": ("discharge", True),
    "sensor.alphaess_daily_battery_discharge": ("discharge", True),
    "sensor.alphaess_grid_to_battery": ("grid_charge", False),
    "sensor.alphaess_daily_grid_charge": ("grid_charge", False),
    "sensor.alphaess_solar_to_battery": ("solar_charge", True),
    "sensor.alphaess_solar_to_load": ("solar_load", True),
    "sensor.alphaess_total_load": ("load", True),
    "sensor.alphaess_ev_charger": ("ev", False),
    "sensor.alphaess_daily_ev_charging_energy": ("ev", False),
    "sensor.alphaess_today_s_income": ("export", False),
    "sensor.alphaess_total_income": ("export", False),
}
MEANS = {
    "sensor.alphaess_instantaneous_generation": "p_pv",
    "sensor.alphaess_instantaneous_load": "p_load",
    "sensor.alphaess_instantaneous_battery_i_o": "p_battery",
    "sensor.alphaess_instantaneous_grid_i_o_total": "p_grid",
    "sensor.alphaess_instantaneous_battery_soc": "soc",
}

# Frozen hours of this statistic mark every Alpha ESS statistic's hour as bad.
REFERENCE = "sensor.alphaess_instantaneous_load"

# Runs are kept small for the 1 GB Pi: a 35-day run (840 hours) took over
# 30 s and pushed it into swap. For older gaps, pass start and end instead:
# only the statistics around that range are read.
MAX_HOURS = 24 * 7

RUN_SCHEMA = vol.Schema({
    vol.Optional("hours", default=48): vol.All(vol.Coerce(int), vol.Range(min=2, max=MAX_HOURS)),
    # Fill these hours (at most MAX_HOURS), even if they look fine (to redo a
    # bad fill), and any gap within a day after them.
    vol.Inclusive("start", "range"): cv.datetime,
    vol.Inclusive("end", "range"): cv.datetime,
    vol.Optional("dry_run", default=False): cv.boolean,
})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def run(call: ServiceCall) -> ServiceResponse:
        forced = set()
        if "start" in call.data:
            t = dt_util.as_utc(dt_util.as_local(call.data["start"])).replace(minute=0, second=0, microsecond=0)
            end = dt_util.as_utc(dt_util.as_local(call.data["end"]))
            while t < end:
                forced.add(t)
                t += gaps.HOUR
            if len(forced) > MAX_HOURS:
                raise HomeAssistantError(f"start to end is more than {MAX_HOURS} hours")
        return await _run(hass, call.data["hours"], call.data["dry_run"], forced)

    hass.services.async_register(
        DOMAIN, "run", run, schema=RUN_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    return True


class _Cloud:
    def __init__(self, hass: HomeAssistant) -> None:
        entries = hass.config_entries.async_entries("alphaess")
        if not entries:
            raise HomeAssistantError("No Alpha ESS config entry")
        self._id = entries[0].data["AppID"]
        self._secret = entries[0].data["AppSecret"]
        self._session = async_get_clientsession(hass)
        self._sn: str | None = None
        self._days: dict = {}

    async def _get(self, path: str, **params):
        ts = str(int(time.time()))
        sign = hashlib.sha512((self._id + self._secret + ts).encode()).hexdigest()
        headers = {"appId": self._id, "timeStamp": ts, "sign": sign}
        timeout = aiohttp.ClientTimeout(total=30)
        async with self._session.get(API + path, params=params, headers=headers, timeout=timeout) as r:
            body = await r.json(content_type=None)
        if body.get("code") != 200:
            raise HomeAssistantError(f"Alpha ESS {path}: {body.get('code')} {body.get('msg')}")
        return body["data"]

    async def hours(self, days: set) -> dict:
        """Cloud readings by hour for these local dates."""
        if self._sn is None:
            self._sn = (await self._get("getEssList"))[0]["sysSn"]
        tz = dt_util.get_default_time_zone()
        samples = []
        for day in sorted(days):
            if day not in self._days:
                self._days[day] = await self._get(
                    "getOneDayPowerBySn", sysSn=self._sn, queryDate=day.isoformat()
                ) or []
            for x in self._days[day]:
                t = datetime.strptime(x["uploadTime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
                samples.append((t, x))
        return gaps.by_hour(samples)


async def _run(hass: HomeAssistant, hours: int, dry_run: bool, forced: set) -> dict:
    recorder = get_instance(hass)
    end = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    if forced:
        # The row before the range, and the catch-up row within a day after it.
        start = min(forced) - gaps.HOUR
        end = min(end, max(forced) + timedelta(hours=25))
    else:
        start = end - timedelta(hours=hours)
    ids = set(SUMS) | set(MEANS)
    stats = await recorder.async_add_executor_job(
        statistics_during_period, hass, start, end, ids, "hour", None, {"sum", "mean", "min", "max"}
    )
    meta = await recorder.async_add_executor_job(lambda: get_metadata(hass, statistic_ids=ids))
    cloud = _Cloud(hass)
    report: dict = {}
    tz = dt_util.get_default_time_zone()
    rows_of = {
        stat_id: [dict(r, start=dt_util.utc_from_timestamp(r["start"])) for r in rows]
        for stat_id, rows in stats.items()
    }
    bad = gaps.stale_hours(rows_of.get(REFERENCE, [])) | forced

    for stat_id in sorted(ids):
        if stat_id not in meta or not rows_of.get(stat_id):
            continue
        is_sum = stat_id in SUMS
        for a, missing, c in gaps.find_gaps(rows_of[stat_id], "sum" if is_sum else "mean", bad):
            span = missing + [c["start"]]
            key = (
                f"{stat_id} {missing[0].astimezone(tz):%Y-%m-%d %H:%M}"
                f"–{c['start'].astimezone(tz):%Y-%m-%d %H:%M}"
            )
            try:
                by_hour = await cloud.hours({h.astimezone(tz).date() for h in span})
            except Exception as err:  # noqa: BLE001 - report and try again next hour
                report[key] = f"cloud error: {err}"
                continue
            if not gaps.covered(by_hour, span if is_sum else missing):
                report[key] = "cloud has no readings for these hours yet"
                continue
            if is_sum:
                flow, comparable = SUMS[stat_id]
                new, adjustment, mode = gaps.fill_sum(a, missing, c, by_hour, flow, comparable)
            else:
                new, adjustment, mode = gaps.fill_mean(missing, by_hour, MEANS[stat_id]), 0.0, "cloud"
            report[key] = {"mode": mode, "hours": len(new), "adjustment": round(adjustment, 3)}
            if dry_run or not new:
                continue
            m = meta[stat_id][1]
            metadata = {
                "source": "recorder",
                "statistic_id": stat_id,
                "name": None,
                "has_sum": m["has_sum"],
                "mean_type": m["mean_type"],
                "unit_class": m.get("unit_class"),
                "unit_of_measurement": m["unit_of_measurement"],
            }
            async_import_statistics(hass, metadata, new)
            if adjustment:
                recorder.async_adjust_statistics(stat_id, c["start"], adjustment, m["unit_of_measurement"])
            _LOGGER.info("Filled %s: %s", key, report[key])
    return {"filled": report, "dry_run": dry_run}
