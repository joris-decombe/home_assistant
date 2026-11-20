# power.dx2-66.com

The public page about our roof's solar. Home Assistant sends each finished day,
hour by hour, and the page shows daily totals, an average day's solar and the
weather. The Worker that serves it (`dx2-66-power`, `worker/power.js`) is in
the dx2-66 repo. Here, `config/packages/public_stats.yaml` does the sending.

## What gets sent

`script.public_stats_send` reads the recorder's hourly statistics (`change` and
`state`) for 7 sensors and posts one day per request to
`https://power.dx2-66.com/push`:

| Field | Statistic |
|---|---|
| `solar_kwh` | `sensor.alphaess_solar_production` |
| `import_kwh` | `sensor.alphaess_grid_to_load` |
| `export_kwh` | `sensor.alphaess_solar_to_grid` |
| `battery_charge_kwh` | `sensor.alphaess_charge` |
| `battery_discharge_kwh` | `sensor.alphaess_discharge` |
| `car_kwh` | `sensor.garage_joris_home_charger_energy_meter` |
| `car_roof_kwh` | `sensor.car_energy_from_the_roof` |

Each hour is keyed by its start in UTC (`2026-11-19T00:00:00Z`) and can carry
`estimated: true`. The automation runs at 00:40 for yesterday and the 2 days
before, then hourly and at start until yesterday has gone through whole
(`input_text.public_stats_pushed`). By hand, `days` goes up to 14.

The push secret (`public_stats_push_auth` in the Pi's `secrets.yaml`, and
`PUSH_SECRET` on the Worker) can:

- replace any hour of today or yesterday;
- on older days (up to 400 days back), fill hours the page doesn't have, and
  replace an estimated hour with another estimate. A measured hour is never
  replaced, and a measured value can't replace an estimate either.

So resending is harmless, and a better estimate can always replace an older one.

## Hours Home Assistant missed

When HA is down or an integration is stuck, the statistics show hours with
nothing, then one hour holding all that piled up. The script spreads that
catch-up back over the gap (solar, export and battery charge along the roof's
usual day, the rest evenly) and marks those hours estimated, with three
exceptions:

- **Alpha ESS's counters start again at midnight.** A catch-up only holds its
  own day. When a gap crosses midnight, the catch-up becomes the counter's
  reading (its `state`, the kWh since midnight), spread from midnight, and the
  missed hours of the days before stay empty. The page estimates a day with
  fewer than 20 hours from the days around it.
- **The car's meter doesn't reset**, but its catch-up also lands in one hour.
  When Evnex's sessions (`sensor.garage_joris_home_charger_session_history`,
  the last 10) account for a car gap, its hours take the sessions' charging.
  A day whose sessions hold more than the statistic also takes them.
- **More than 8 kWh of charging in an hour** is the meter catching up. That
  hour takes the sessions' charging, so its solar isn't dropped with it.

A catch-up that's too small to be real (under 0.15 kWh per hour covered, or
under 30% of an average day's solar) isn't spread: the gap stays empty.

## When a day looks wrong on the page

1. Compare it with the Alpha ESS app (Energy, Day): Total Generated is the
   solar and Total Used is the house's use, cars included.
2. If HA's statistics are right (check with `recorder.get_statistics`, or the
   Energy dashboard), run `script.public_stats_send` with enough `days` to
   cover it. Hours the page holds as estimated get replaced; measured ones
   stay.
3. If HA lost the data, first try to get it back into HA's statistics (Alpha
   ESS's own history). Otherwise push the day by hand as estimated hours: the
   app's day totals, shaped like a similar measured day, with the car from
   Evnex's sessions. The secret is in `.claude/power-push.env.local`
   (gitignored); never print it.

## 17 to 19 November 2026

Alpha ESS was stuck from 11:00 on 17 November to 23:00 on the 19th, and HA
itself was down for most of the 19th's afternoon. Its counters froze at the 17th's morning
reading (4.0 kWh of solar), so when they came back at 30 kWh, HA counted a
26 kWh catch-up. The script spread it over the three days: the page showed
about 10 kWh a day, where the app had 14.8, 19.4 and 30. The car's meter was
out too, and caught up with 19.3 kWh at 09:00 on the 20th, which made the
script drop that hour.

Fixed on 21 November: 19 November was first refilled from Alpha's day totals
in HA (the counters' readings at 23:00), and 17 and 18 November from the app's
totals. Then Alpha ESS's history was imported back into HA's statistics, the
script got the three fixes above, and a run with `days: 5` replaced all three
days and 20 November with HA's real hours (still marked estimated, since the
car's charging comes from the sessions). 17 November now shows 14.0 kWh,
0.8 less than the app.
