"""Play a sound on media players when the grid is lost or comes back, and on battery levels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
import logging

from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_VOLUME_SET, STATE_OFF, STATE_ON
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import BATTERY_LEVELS, DEFAULT_VOLUME, EVENT_LOST, EVENT_RESTORED

_LOGGER = logging.getLogger(__name__)

# vlc_telnet sends volume_level * 500, but aiovlc only accepts 0..499, so 1.0 fails.
MAX_VOLUME_LEVEL = 0.99


def in_window(now: time, window: tuple[time, time]) -> bool:
    start, end = window
    if start < end:
        return start <= now < end
    return now >= start or now < end  # crosses midnight


@dataclass(frozen=True)
class Player:
    """A media player that plays the sounds (one per player subentry)."""

    id: str
    entity_id: str
    sounds: dict[str, dict[str, str]]  # event (grid or battery level) -> media content id/type
    volume: float  # 0..1
    window: tuple[time, time] | None = None  # local start, end; may cross midnight
    battery_volume: float = DEFAULT_VOLUME / 100  # 0..1, for the battery levels


class Announcer:
    """Grid lost (on → off) and restored (off → on), and battery levels, inside each player's window.

    Only a direct on → off or off → on of the grid entity counts: unavailable or unknown in between
    (the inverter out of sight) says nothing.
    """

    def __init__(self, hass: HomeAssistant, grid_entity: str | None) -> None:
        self.hass = hass
        self.grid_entity = grid_entity
        self.players: dict[str, Player] = {}
        self.enabled: dict[str, bool] = {}  # player id -> its "Sound notifications" switch
        self._listeners: list[CALLBACK_TYPE] = []
        self._unsub: CALLBACK_TYPE | None = None

    @callback
    def async_start(self) -> None:
        if self.grid_entity:
            self._unsub = async_track_state_change_event(self.hass, self.grid_entity, self._async_grid_changed)

    @callback
    def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def async_add_listener(self, listener: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Called when a switch flag changes."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def async_notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def _async_grid_changed(self, event: Event[EventStateChangedData]) -> None:
        old, new = event.data["old_state"], event.data["new_state"]
        old_state, new_state = old.state if old else None, new.state if new else None
        if old_state == STATE_ON and new_state == STATE_OFF:
            self._announce(EVENT_LOST)
        elif old_state == STATE_OFF and new_state == STATE_ON:
            self._announce(EVENT_RESTORED)

    @callback
    def async_battery_level(self, level: str) -> None:
        """A battery level was crossed; same switch and window as the grid sounds."""
        self._announce(level)

    @callback
    def _announce(self, event: str) -> None:
        now = dt_util.now().time()
        for player in self.players.values():
            if not self.enabled.get(player.id, True):
                continue
            if player.window is not None and not in_window(now, player.window):
                _LOGGER.debug("%s: %s is outside its window", event, player.entity_id)
                continue
            self.hass.async_create_task(self._async_play(player, event))

    async def async_test(self, player_id: str, event: str) -> None:
        """Play the sound for ``event`` now, ignoring the window and the switch."""
        await self._async_play(self.players[player_id], event)

    async def _async_play(self, player: Player, event: str) -> None:
        sound = player.sounds.get(event)
        if sound is None:
            return
        _LOGGER.info("%s: playing %s on %s", event, sound[ATTR_MEDIA_CONTENT_ID], player.entity_id)
        target = {ATTR_ENTITY_ID: player.entity_id}
        volume = player.battery_volume if event in BATTERY_LEVELS else player.volume
        try:
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_VOLUME_SET,
                {**target, ATTR_MEDIA_VOLUME_LEVEL: min(volume, MAX_VOLUME_LEVEL)},
                blocking=True,
            )
        except HomeAssistantError as err:  # a wrong volume is better than no sound
            _LOGGER.warning("%s: can't set volume on %s: %s", event, player.entity_id, err)
        try:
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_PLAY_MEDIA,
                {
                    **target,
                    ATTR_MEDIA_CONTENT_ID: sound[ATTR_MEDIA_CONTENT_ID],
                    ATTR_MEDIA_CONTENT_TYPE: sound[ATTR_MEDIA_CONTENT_TYPE],
                },
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("%s: can't play on %s: %s", event, player.entity_id, err)
