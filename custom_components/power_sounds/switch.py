"""Per-player switch: whether it plays the sounds (mirrors the subentry flag)."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PowerSoundsConfigEntry
from .announcer import Announcer, Player
from .const import CONF_ENABLED


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerSoundsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    announcer = entry.runtime_data.announcer
    for player in announcer.players.values():
        async_add_entities([PlayerSwitch(hass, entry, announcer, player)], config_subentry_id=player.id)


class PlayerSwitch(SwitchEntity):
    """On: this player plays the sounds inside its window."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bullhorn-outline"

    def __init__(
        self, hass: HomeAssistant, entry: PowerSoundsConfigEntry, announcer: Announcer, player: Player
    ) -> None:
        self._entry = entry
        self._announcer = announcer
        self._player = player
        self._attr_unique_id = f"{player.id}_{CONF_ENABLED}"
        self._attr_translation_key = "announce"
        self.device_entry = async_entity_id_to_device(hass, player.entity_id)
        if self.device_entry is None:
            self._attr_translation_key = "announce_named"
            self._attr_translation_placeholders = {"player": entry.subentries[player.id].title}

    @property
    def is_on(self) -> bool:
        return self._announcer.enabled.get(self._player.id, True)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        if self._player.window is None:
            return None
        start, end = self._player.window
        return {"window_start": start.isoformat(), "window_end": end.isoformat()}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._announcer.async_add_listener(self._on_change))

    async def async_turn_on(self, **kwargs) -> None:
        self._write(True)

    async def async_turn_off(self, **kwargs) -> None:
        self._write(False)

    def _write(self, value: bool) -> None:
        subentry = self._entry.subentries[self._player.id]
        self.hass.config_entries.async_update_subentry(self._entry, subentry, data={**subentry.data, CONF_ENABLED: value})

    @callback
    def _on_change(self) -> None:
        self.async_write_ha_state()
