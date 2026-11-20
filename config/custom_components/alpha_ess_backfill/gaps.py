"""Gap finding and filling, with no Home Assistant imports (testable anywhere).

A gap is a run of missing or frozen hours in a statistic's hourly rows,
closed by a catch-up row: the first hour HA had live data again. For an energy (sum)
statistic, the catch-up row holds all the energy of the gap. It is spread
back over the gap hours and the catch-up hour along the Alpha ESS cloud's
power readings for the same hours. For a power (mean) statistic, the gap
hours get the mean, min and max of the cloud's readings.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

HOUR = timedelta(hours=1)
# A longer pause between readings counts as missing. Uploads buffered while
# offline have holes of 10-15 minutes (21 November 2026, 05:00).
MAX_SAMPLE = timedelta(minutes=30)
MIN_COVERAGE = 0.8  # share of each hour the cloud readings must cover


def flows(x: dict) -> dict[str, float]:
    """Power flows (W) of one cloud reading (getOneDayPowerBySn).

    pbat is positive when the battery discharges, as in HA's battery_i_o.
    gridCharge is the power bought from the grid, feedIn the power sold.
    """
    ppv = max(x.get("ppv") or 0, 0)
    load = max(x.get("load") or 0, 0)
    grid = max(x.get("gridCharge") or 0, 0)
    feed = max(x.get("feedIn") or 0, 0)
    pbat = x.get("pbat") or 0
    charge, discharge = max(-pbat, 0), max(pbat, 0)
    return {
        "pv": ppv,
        "import": grid,
        "export": feed,
        "charge": charge,
        "discharge": discharge,
        "grid_charge": min(grid, charge),
        "solar_charge": min(ppv, charge),
        "solar_load": min(ppv, load),
        "load": load,
        "ev": max(x.get("pchargingPile") or 0, 0),
        # Power sensors, signed like HA's.
        "p_pv": ppv,
        "p_load": load,
        "p_battery": pbat,
        "p_grid": (x.get("gridCharge") or 0) - (x.get("feedIn") or 0),
        "soc": x.get("cbat"),
    }


def by_hour(samples: list[tuple[datetime, dict]]):
    """Cloud readings (aware local time, reading) grouped by the hour they cover.

    Each reading stands for the time since the one before it, so it counts in
    the hour of that interval's midpoint. Returns {hour start (UTC): {"seconds": s,
    "kwh": {flow: kWh}, "values": {flow: [(weight, W)]}}}.
    """
    out: dict[datetime, dict] = defaultdict(
        lambda: {"seconds": 0.0, "kwh": defaultdict(float), "values": defaultdict(list)}
    )
    samples = sorted(samples, key=lambda s: s[0])
    prev = None
    for t, x in samples:
        dt = (t - prev) if prev is not None else timedelta(minutes=5)
        prev = t
        if dt <= timedelta(0) or dt > MAX_SAMPLE:
            continue
        mid = (t - dt / 2).astimezone(timezone.utc)
        hour = mid.replace(minute=0, second=0, microsecond=0)
        h = out[hour]
        sec = dt.total_seconds()
        h["seconds"] += sec
        for k, w in flows(x).items():
            if w is None:
                continue
            h["kwh"][k] += w * sec / 3_600_000
            h["values"][k].append((sec, w))
    return out


def stale_hours(rows: list[dict]) -> set[datetime]:
    """Hours a power statistic didn't move at all (min == max).

    Alpha ESS can freeze rather than go unavailable: every entity keeps its
    last value for days (17-19 November 2026: 48 hours at 1153 W). The house
    load is never flat for a whole hour when the integration is live.
    """
    return {r["start"] for r in rows if r.get("min") is not None and r["min"] == r.get("max")}


def find_gaps(rows: list[dict], key: str, bad: set[datetime] = frozenset()):
    """(row before, [hours to fill], catch-up row) for each gap.

    An hour is in a gap when it has no row, or is in `bad` (frozen, or a
    range asked for). rows: hourly statistics rows sorted by start, with
    "start" as an aware UTC datetime and `key` ("sum" or "mean") set.
    """
    rows = [r for r in rows if r.get(key) is not None]
    if not rows:
        return
    by_start = {r["start"]: r for r in rows}
    t, last = rows[0]["start"], rows[-1]["start"]
    a, run = None, []
    while t <= last:
        r = by_start.get(t)
        if r is None or t in bad:
            if a is not None:
                run.append(t)
        else:
            if run:
                yield a, run, r
            a, run = r, []
        t += HOUR


def covered(cloud, hours) -> bool:
    return all(
        cloud.get(h) is not None and cloud[h]["seconds"] >= MIN_COVERAGE * 3600
        for h in hours
    )


def fill_sum(a: dict, missing: list[datetime], c: dict, cloud, flow: str, comparable: bool):
    """New rows for the missing hours, and the adjustment for the catch-up row on.

    By default the catch-up's own energy is spread along the cloud's shape, so
    every sum from the catch-up row on stays as it is. When the catch-up is
    clearly short of the cloud's energy (a daily meter that reset at midnight
    during the gap loses the evening before it), the cloud's energy is used
    instead and the sums from the catch-up row on move by the difference.
    Only flows whose integrated readings match the inverter's own counters
    (within ~8% over a day, checked November 2026) are `comparable`: export
    and grid charging come in short bursts the readings miss.
    Returns (rows, adjustment, mode).
    """
    hours = missing + [c["start"]]
    energy = [cloud[h]["kwh"].get(flow, 0.0) for h in hours]
    total = sum(energy)
    change = c["sum"] - a["sum"]
    adjustment = 0.0
    if comparable and total - change > max(0.2 * total, 0.3):
        mode = "cloud"
        adjustment = total - change
    elif total > 0 and change >= 0:
        mode = "spread"
        energy = [e * change / total for e in energy]
    else:
        mode = "flat"  # no shape to follow: the energy stays in the catch-up hour
        energy = [0.0] * len(missing) + [change]
    rows, s = [], a["sum"]
    for h, e in zip(missing, energy):
        s += e
        rows.append({"start": h, "sum": s})
    return rows, adjustment, mode


def fill_mean(missing: list[datetime], cloud, flow: str):
    rows = []
    for h in missing:
        vals = cloud[h]["values"].get(flow) or []
        if not vals:
            continue
        weight = sum(w for w, _ in vals)
        rows.append({
            "start": h,
            "mean": sum(w * v for w, v in vals) / weight,
            "min": min(v for _, v in vals),
            "max": max(v for _, v in vals),
        })
    return rows
