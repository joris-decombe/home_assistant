# Raspberry Pi image

Builds a flashable Home Assistant OS image for a Raspberry Pi: the official HAOS
release, verified against its published SHA-256, with optional network and SSH
settings pre-loaded so the Pi comes up on the right address on first boot.

## Build

Needs Docker. From the repo root, in PowerShell:

```powershell
cp rpi/image.env.example rpi/image.env   # then edit it
docker build -t haos-rpi-builder rpi
docker run --rm -v "${PWD}/rpi:/work" --env-file rpi/image.env haos-rpi-builder
```

Output: `rpi/build/haos_<board>-<version>-custom.img` (about 900 MB). The
downloaded `.img.xz` is cached in `rpi/build/` and re-verified on every run.

### Settings (`rpi/image.env`)

| Variable | Default | Meaning |
|---|---|---|
| `HAOS_BOARD` | `rpi3-64` | `rpi3-64`, `rpi4-64` or `rpi5-64` |
| `HAOS_VERSION` | `latest` | HAOS release tag, e.g. `18.3` |
| `NET_INTERFACE` | `ethernet` | `ethernet` or `wifi` |
| `WIFI_SSID`, `WIFI_PSK` | | Required for `wifi` (Pi 3 is 2.4 GHz only) |
| `NET_ADDRESS` | DHCP | Static IPv4 in CIDR, e.g. `192.168.68.50/24` |
| `NET_GATEWAY` | | Required with `NET_ADDRESS` |
| `NET_DNS` | gateway | DNS server |
| `SSH_AUTHORIZED_KEY` | | Public key for host debug SSH (`root`, port 22222) |

With every value left at its default, the image is stock HAOS (Ethernet + DHCP).
Anything set is written to a `CONFIG/` folder on the boot partition; HAOS imports it
on first boot and then deletes it. To change these later, use
Settings → System → Network in Home Assistant.

A static address is worth setting. The VM's DHCP address changed once already
(192.168.0.35 → 192.168.68.93), which broke the MCP config. Pick an address outside
the router's DHCP pool, or reserve one for the Pi's MAC address in the router.

`image.env` holds the Wi-Fi password if you use Wi-Fi. It is gitignored, but the built
image contains the password too, so don't share the image.

## Flash

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) → *Choose OS* →
*Use custom* → pick the `.img`, then choose the target drive. Skip Imager's
"OS customisation"; it applies to Raspberry Pi OS, not HAOS.
[balenaEtcher](https://etcher.balena.io/) works too.

### SD card or SSD

Prefer a 2.5" SATA SSD in a USB-to-SATA adapter over an SD card. The recorder
database writes constantly and wears SD cards out. Flash the image to the SSD the same
way as to a card.

- **Pi 3B+, Pi 4, Pi 5**: boot from USB with no SD card inserted. A Pi 4 with an old
  bootloader may need updating first (Raspberry Pi Imager → *Misc utility images* →
  *Bootloader* → *USB Boot*).
- **Original Pi 3B**: USB boot is off by default and is enabled once by burning an
  OTP bit. Boot Raspberry Pi OS from an SD card, add `program_usb_boot_mode=1` to
  `/boot/firmware/config.txt`, reboot, and check that
  `vcgencmd otp_dump | grep 17:` shows `3020000a`. After that the SD card can be
  removed.
- Use a 2.5 A official supply. On a Pi 3 the SSD shares the USB 2.0 bus with
  Ethernet, so throughput is modest, but it is still more reliable than an SD card.
- Some cheap USB-SATA bridges misbehave with UAS. If the Pi fails to boot or the
  disk drops out, try a different adapter.

## First boot

1. Connect Ethernet (unless using Wi-Fi) and power on. First boot takes 5–20 minutes
   on a Pi 3 while HAOS downloads the latest Home Assistant Core.
2. Open `http://homeassistant.local:8123`, or the static IP if you set one.
3. Onboard: create the admin user, set location to Wellington (`Pacific/Auckland`,
   NZD, NZ).
4. Create a Long-Lived Access Token and point `HASS_HOST` in
   `.claude/settings.local.json` at the Pi.

## Hardware notes

A Pi 3 has 1 GB of RAM. HAOS still supports it (`rpi3-64` ships in 18.3), but
HACS, Alpha ESS Modbus, OCPP and the recorder together will run close to the limit.
If you buy new hardware, a Pi 4 or Pi 5 with 4 GB+ RAM gives plenty of headroom; set
`HAOS_BOARD` to match and rebuild.
