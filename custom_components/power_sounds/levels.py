"""Battery levels: each crossed once per discharge, from a charge sensor and a time-left sensor.

A charge level is crossed when the charge falls below it; a time-left level when the time left is at
or under it. A level comes back only after ``REARM_PERCENT`` points of real charging, so a short blink
of the grid or a jitter of the estimate repeats nothing. If several are crossed together, only the
most urgent is reported. The passed levels are stored, so a restart in the middle of a discharge
repeats nothing; on the very first start the levels already below are taken as passed, silently.
"""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import BATTERY_LEVELS, DOMAIN, REARM_PERCENT, RUNTIME_LEVELS, SOC_LEVELS, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

SAVE_DELAY = 10


def _number(state) -> float | None:
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


class LevelTracker:
    """Report each battery level crossed while discharging."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        soc_entity: str,
        runtime_entity: str | None,
        on_level: Callable[[str], None],
    ) -> None:
        self.hass = hass
        self.soc_entity = soc_entity
        self.runtime_entity = runtime_entity
        self._on_level = on_level
        self.soc: float | None = None
        self.runtime: float | None = None
        self.passed: set[str] = set()
        self._low: float | None = None  # lowest charge since the time-left levels were re-armed
        self._first_start = False
        self._unsubs: list[CALLBACK_TYPE] = []
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.levels")

    @property
    def levels(self) -> tuple[str, ...]:
        """The levels this tracker can report: time left only with a time-left sensor."""
        return tuple(level for level in BATTERY_LEVELS if level in SOC_LEVELS or self.runtime_entity)

    async def async_load(self) -> None:
        data = await self._store.async_load()
        self._first_start = data is None
        data = data or {}
        self.passed = set(data.get("passed", [])) & set(BATTERY_LEVELS)
        self._low = data.get("low")

    @callback
    def async_start(self) -> None:
        self.soc = _number(self.hass.states.get(self.soc_entity))
        if self.runtime_entity:
            self.runtime = _number(self.hass.states.get(self.runtime_entity))
        if self._first_start:
            self.passed = set(self._crossed())
            self._low = self.soc
            self._save()
        elif self.soc is not None:
            self._rearm(self.soc)
        entities = [self.soc_entity] + ([self.runtime_entity] if self.runtime_entity else [])
        self._unsubs.append(async_track_state_change_event(self.hass, entities, self._async_changed))

    @callback
    def async_stop(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()

    async def async_flush(self) -> None:
        await self._store.async_save(self._data())

    def _data(self) -> dict:
        return {"passed": sorted(self.passed), "low": self._low}

    def _save(self) -> None:
        self._store.async_delay_save(self._data, SAVE_DELAY)

    @callback
    def _async_changed(self, event: Event[EventStateChangedData]) -> None:
        value = _number(event.data["new_state"])
        if event.data["entity_id"] != self.soc_entity:
            self.runtime = value  # unknown while charging or idle: no stale estimate
            if value is not None and self._check():
                self._save()
            return
        if value is None:
            return
        previous, self.soc = self.soc, value
        changed = self._rearm(value)
        if previous is not None and value < previous:  # charge levels only matter on the way down
            changed = self._check() or changed
        if changed:
            self._save()

    def _crossed(self) -> list[str]:
        crossed = []
        for level in self.levels:
            if level in self.passed:
                continue
            if level in SOC_LEVELS:
                hit = self.soc is not None and self.soc < SOC_LEVELS[level]
            else:
                hit = self.runtime is not None and self.runtime <= RUNTIME_LEVELS[level]
            if hit:
                crossed.append(level)
        return crossed

    def _check(self) -> bool:
        if not (crossed := self._crossed()):
            return False
        self.passed.update(crossed)
        _LOGGER.info("Battery at %s %%, %s min left: %s", self.soc, self.runtime, crossed)
        self._on_level(crossed[0])  # one player can't say several at once: the most urgent only
        return True

    def _rearm(self, soc: float) -> bool:
        """Bring levels back after a real charge; return whether the stored data changed."""
        before = (set(self.passed), self._low)
        self.passed -= {level for level, value in SOC_LEVELS.items() if soc >= value + REARM_PERCENT}
        if self._low is None or soc < self._low:
            self._low = soc
        elif soc >= self._low + REARM_PERCENT:
            self.passed -= set(RUNTIME_LEVELS)
            self._low = soc
        return (self.passed, self._low) != before
