"""Power Sounds: sounds on grid loss and return and on battery levels."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .announcer import Announcer, Player
from .const import (
    BATTERY_LEVELS,
    CONF_BATTERY_VOLUME,
    CONF_ENABLED,
    CONF_GRID_ENTITY,
    CONF_MEDIA_PLAYER,
    CONF_RUNTIME_ENTITY,
    CONF_SOC_ENTITY,
    CONF_SOUND_LOST,
    CONF_SOUND_RESTORED,
    CONF_VOLUME,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_VOLUME,
    EVENT_LOST,
    EVENT_RESTORED,
    SUBENTRY_PLAYER,
)
from .levels import LevelTracker

PLATFORMS = [Platform.BUTTON, Platform.SWITCH]


@dataclass
class RuntimeData:
    announcer: Announcer
    levels: LevelTracker | None
    signature: tuple


type PowerSoundsConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: PowerSoundsConfigEntry) -> bool:
    opts = entry.options
    announcer = Announcer(hass, opts.get(CONF_GRID_ENTITY) or None)
    levels: LevelTracker | None = None
    if soc_entity := opts.get(CONF_SOC_ENTITY):
        levels = LevelTracker(
            hass,
            entry.entry_id,
            soc_entity=soc_entity,
            runtime_entity=opts.get(CONF_RUNTIME_ENTITY) or None,
            on_level=announcer.async_battery_level,
        )
        await levels.async_load()

    ent_reg = er.async_get(hass)
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_PLAYER:
            continue
        entity_id = er.async_resolve_entity_id(ent_reg, subentry.data[CONF_MEDIA_PLAYER])
        if entity_id is None:
            continue  # the player was deleted; its subentry stays until the user removes it
        data = subentry.data
        sounds = {
            event: data[key]
            for event, key in ((EVENT_LOST, CONF_SOUND_LOST), (EVENT_RESTORED, CONF_SOUND_RESTORED))
            if data.get(key)
        }
        sounds |= {level: sound for level in BATTERY_LEVELS if (sound := data.get(f"sound_{level}"))}
        announcer.players[subentry_id] = Player(
            subentry_id,
            entity_id,
            sounds,
            data.get(CONF_VOLUME, DEFAULT_VOLUME) / 100,
            _window(data),
            data.get(CONF_BATTERY_VOLUME, DEFAULT_VOLUME) / 100,
        )
    _apply_flags(entry, announcer)

    entry.runtime_data = RuntimeData(announcer, levels, _signature(entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    announcer.async_start()
    entry.async_on_unload(announcer.async_stop)
    if levels:
        levels.async_start()
        entry.async_on_unload(levels.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PowerSoundsConfigEntry) -> bool:
    if entry.runtime_data.levels:
        await entry.runtime_data.levels.async_flush()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _window(data) -> tuple | None:
    start, end = data.get(CONF_WINDOW_START), data.get(CONF_WINDOW_END)
    return (dt_util.parse_time(start), dt_util.parse_time(end)) if start and end else None


def _signature(entry: PowerSoundsConfigEntry) -> tuple:
    """Everything except the on/off flags; a change here needs a reload."""
    return (
        tuple(sorted(entry.options.items())),
        tuple(
            sorted(
                (sid, repr(sorted((k, v) for k, v in sub.data.items() if k != CONF_ENABLED)))
                for sid, sub in entry.subentries.items()
            )
        ),
    )


def _apply_flags(entry: PowerSoundsConfigEntry, announcer: Announcer) -> None:
    for player_id in announcer.players:
        announcer.enabled[player_id] = entry.subentries[player_id].data.get(CONF_ENABLED, True)


async def _async_entry_updated(hass: HomeAssistant, entry: PowerSoundsConfigEntry) -> None:
    """Options or players changed: apply flag-only changes live, reload for anything else."""
    data = entry.runtime_data
    if _signature(entry) == data.signature:
        _apply_flags(entry, data.announcer)
        data.announcer.async_notify()
        return
    await hass.config_entries.async_reload(entry.entry_id)
