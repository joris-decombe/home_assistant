#!/bin/sh
# Builds a flashable Home Assistant OS image for a Raspberry Pi.
#
# Downloads the official HAOS release, verifies its SHA-256 against the
# GitHub release digest, decompresses it, and drops a CONFIG/ folder on the
# boot partition. HAOS imports that folder once on first boot (network
# connection, debug SSH key) and then deletes it.
#
# Runs inside the container from ./Dockerfile; see README.md for usage.
set -eu

BOARD=${HAOS_BOARD:-rpi3-64}
VERSION=${HAOS_VERSION:-latest}
OUT=/work/build
API=https://api.github.com/repos/home-assistant/operating-system/releases

die() { echo "error: $*" >&2; exit 1; }

case "$BOARD" in
  rpi3-64|rpi4-64|rpi5-64) ;;
  *) die "HAOS_BOARD must be rpi3-64, rpi4-64 or rpi5-64 (got '$BOARD')" ;;
esac

mkdir -p "$OUT"

if [ "$VERSION" = latest ]; then
  release=$(curl -fsSL "$API/latest")
else
  release=$(curl -fsSL "$API/tags/$VERSION")
fi
VERSION=$(echo "$release" | jq -r .tag_name)
asset="haos_${BOARD}-${VERSION}.img.xz"
url=$(echo "$release" | jq -r --arg n "$asset" '.assets[] | select(.name == $n) | .browser_download_url')
digest=$(echo "$release" | jq -r --arg n "$asset" '.assets[] | select(.name == $n) | .digest // empty')
[ -n "$url" ] || die "release $VERSION has no asset $asset"
[ -n "$digest" ] || die "release $VERSION publishes no digest for $asset; refusing to build unverified"
sha=${digest#sha256:}

verify() { echo "$sha  $OUT/$asset" | sha256sum -c - >/dev/null 2>&1; }

if [ -f "$OUT/$asset" ] && verify; then
  echo "Using cached $asset"
else
  echo "Downloading $asset"
  curl -fL --progress-bar -o "$OUT/$asset.part" "$url"
  mv "$OUT/$asset.part" "$OUT/$asset"
  verify || die "checksum mismatch for $asset"
fi
echo "Checksum OK ($sha)"

img="$OUT/haos_${BOARD}-${VERSION}-custom.img"
echo "Decompressing to $(basename "$img")"
xz -dc "$OUT/$asset" > "$img"

# The first partition is the FAT boot partition (hassos-boot) on every RPi board.
table=$(sfdisk -J "$img")
start=$(echo "$table" | jq '.partitiontable.partitions[0].start')
sector=$(echo "$table" | jq '.partitiontable.sectorsize // 512')
export MTOOLS_SKIP_CHECK=1
boot="$img@@$((start * sector))"
mdir -i "$boot" ::config.txt >/dev/null 2>&1 || die "partition 1 is not the Raspberry Pi boot partition"

stage=$(mktemp -d)
cfg="$stage/CONFIG"
mkdir -p "$cfg"

# --- Network -----------------------------------------------------------------
# Only written when something differs from HAOS's default (Ethernet + DHCP).
NET_INTERFACE=${NET_INTERFACE:-ethernet}
NET_ADDRESS=${NET_ADDRESS:-}
if [ "$NET_INTERFACE" = wifi ] || [ -n "$NET_ADDRESS" ]; then
  mkdir -p "$cfg/network"
  conn="$cfg/network/my-network"
  {
    echo "[connection]"
    echo "id=my-network"
    echo "uuid=$(cat /proc/sys/kernel/random/uuid)"
    case "$NET_INTERFACE" in
      ethernet)
        echo "type=802-3-ethernet"
        ;;
      wifi)
        [ -n "${WIFI_SSID:-}" ] || die "NET_INTERFACE=wifi needs WIFI_SSID"
        [ -n "${WIFI_PSK:-}" ] || die "NET_INTERFACE=wifi needs WIFI_PSK"
        echo "type=802-11-wireless"
        echo
        echo "[802-11-wireless]"
        echo "mode=infrastructure"
        echo "ssid=$WIFI_SSID"
        echo
        echo "[802-11-wireless-security]"
        echo "auth-alg=open"
        echo "key-mgmt=wpa-psk"
        echo "psk=$WIFI_PSK"
        ;;
      *) die "NET_INTERFACE must be ethernet or wifi (got '$NET_INTERFACE')" ;;
    esac
    echo
    echo "[ipv4]"
    if [ -n "$NET_ADDRESS" ]; then
      [ -n "${NET_GATEWAY:-}" ] || die "NET_ADDRESS needs NET_GATEWAY"
      echo "method=manual"
      echo "address1=$NET_ADDRESS,$NET_GATEWAY"
      echo "dns=${NET_DNS:-$NET_GATEWAY};"
    else
      echo "method=auto"
    fi
    echo
    echo "[ipv6]"
    echo "addr-gen-mode=stable-privacy"
    echo "method=auto"
  } > "$conn"
  echo "Network: $NET_INTERFACE, ${NET_ADDRESS:-DHCP}"
fi

# --- Host debug SSH (port 22222) ------------------------------------------------
if [ -n "${SSH_AUTHORIZED_KEY:-}" ]; then
  echo "$SSH_AUTHORIZED_KEY" > "$cfg/authorized_keys"
  echo "Debug SSH: enabled on port 22222"
fi

if [ -n "$(ls -A "$cfg")" ]; then
  mcopy -i "$boot" -s "$cfg" ::
  echo "Boot partition CONFIG/:"
  mdir -i "$boot" -/ -b ::CONFIG
else
  echo "No CONFIG overrides set; image is stock HAOS (Ethernet + DHCP)"
fi
rm -rf "$stage"

echo
echo "Done: rpi/build/$(basename "$img")"
