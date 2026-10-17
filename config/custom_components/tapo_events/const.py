"""Constants for Tapo hub camera events."""

from datetime import timedelta

DOMAIN = "tapo_events"
TAPO_CONTROL = "tapo_control"

SCAN_INTERVAL = timedelta(seconds=10)
# Binary sensors stay on this long after an event's end time.
HOLD_SECONDS = 30
# Polls in a row that can fail before the entities go unavailable.
FAILURES_BEFORE_UNAVAILABLE = 3

# Local copies of the hub's detection clips.
MEDIA_ROOT = "/media/tapo"
RETENTION_DAYS = 7
SYNC_INTERVAL_SECONDS = 600
# The hub only serves a clip this long after it ends.
FRESH_SECONDS = 70
# Forget events older than this when deduplicating.
SEEN_TTL_SECONDS = 3600

SIGNAL_NEW_CAMERA = f"{DOMAIN}_new_camera"
SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"

# searchDetectionList fields, observed on C420 behind an H200 (firmware 1.4.2)
# and matching JurajNyiri/HomeAssistant-Tapo-Control#1445 for a C410.
# alarm_type is the main detection; events_1 is a bitmask of everything seen.
ALARM_TYPES = {2: "motion", 6: "person", 8: "vehicle"}
EVENT_BITS = {2: "motion", 32: "person", 128: "vehicle"}

# Event types, most specific first. Unknown codes (pets, say) come out as
# "other", with the raw values in the event's attributes.
EVENT_TYPES = ["person", "vehicle", "motion", "other"]
DETECTIONS = ["motion", "person", "vehicle"]
