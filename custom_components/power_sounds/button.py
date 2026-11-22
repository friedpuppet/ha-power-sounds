"""Test buttons: play a sound now, ignoring the window and the switch."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PowerSoundsConfigEntry
from .announcer import Announcer, Player
from .const import BATTERY_LEVELS, GRID_EVENTS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerSoundsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    data = entry.runtime_data
    events = (GRID_EVENTS if data.announcer.grid_entity else ()) + (BATTERY_LEVELS if data.levels else ())
    for player in data.announcer.players.values():
        async_add_entities(
            [TestSoundButton(hass, entry, data.announcer, player, event) for event in events],
            config_subentry_id=player.id,
        )


class TestSoundButton(ButtonEntity):
    """Play one sound on one player now."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:play-circle-outline"

    def __init__(
        self, hass: HomeAssistant, entry: PowerSoundsConfigEntry, announcer: Announcer, player: Player, event: str
    ) -> None:
        self._announcer = announcer
        self._player_id = player.id
        self._event = event
        key = f"test_sound_{event}"
        self._attr_unique_id = f"{player.id}_{key}"
        self._attr_translation_key = key
        self.device_entry = async_entity_id_to_device(hass, player.entity_id)
        if self.device_entry is None:
            self._attr_translation_key = f"{key}_named"
            self._attr_translation_placeholders = {"player": entry.subentries[player.id].title}

    async def async_press(self) -> None:
        await self._announcer.async_test(self._player_id, self._event)
