"""Constants for Power Sounds."""

from typing import Final

DOMAIN: Final = "power_sounds"

# Entry options: the inputs
CONF_GRID_ENTITY: Final = "grid_entity"  # binary_sensor, on while the flat runs from the grid, optional
CONF_SOC_ENTITY: Final = "soc_entity"  # sensor, battery charge in %, optional
CONF_RUNTIME_ENTITY: Final = "runtime_entity"  # sensor, battery time left in minutes, optional
CONF_STATE_ENTITY: Final = "state_entity"  # sensor, battery state; levels only while it is DISCHARGING, optional
DISCHARGING: Final = "discharging"  # Battery Monitor's state while discharging

# Player subentries
SUBENTRY_PLAYER: Final = "player"
CONF_MEDIA_PLAYER: Final = "media_player"  # entity registry id (or entity_id if unregistered)
CONF_SOUND_LOST: Final = "sound_lost"  # {"media_content_id", "media_content_type"}, optional
CONF_SOUND_RESTORED: Final = "sound_restored"
CONF_VOLUME: Final = "volume"  # percent
CONF_BATTERY_VOLUME: Final = "battery_volume"  # percent, for the battery sounds
CONF_WINDOW_START: Final = "window_start"  # "HH:MM:SS", optional
CONF_WINDOW_END: Final = "window_end"
CONF_ENABLED: Final = "enabled"  # bool, default True
DEFAULT_VOLUME: Final = 50
DEFAULT_WINDOW: Final = ("11:00:00", "22:00:00")

EVENT_LOST: Final = "lost"
EVENT_RESTORED: Final = "restored"
GRID_EVENTS: Final = (EVENT_LOST, EVENT_RESTORED)

# Battery levels; each has an optional sound under the key f"sound_{level}"
SOC_LEVELS: Final = {"soc_25": 25, "soc_50": 50}  # below this percent
RUNTIME_LEVELS: Final = {"runtime_30": 30, "runtime_120": 120}  # minutes left
BATTERY_LEVELS: Final = (*RUNTIME_LEVELS, *SOC_LEVELS)  # most urgent first
REARM_PERCENT: Final = 5.0  # a level comes back only after the battery really charged

STORAGE_VERSION: Final = 1
