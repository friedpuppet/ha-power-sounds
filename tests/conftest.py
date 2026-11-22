"""Fixtures for Power Sounds tests."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant

from custom_components.power_sounds.const import (
    CONF_GRID_ENTITY,
    CONF_MEDIA_PLAYER,
    CONF_RUNTIME_ENTITY,
    CONF_SOC_ENTITY,
    CONF_STATE_ENTITY,
    DOMAIN,
    SUBENTRY_PLAYER,
)

GRID = "binary_sensor.grid"
SOC = "sensor.battery"
RUNTIME = "sensor.battery_time_left"
STATE = "sensor.battery_state"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def make_entry(options: dict[str, Any] | None = None, players: tuple[dict[str, Any], ...] = ()) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Sounds",
        data={},
        options={
            CONF_GRID_ENTITY: GRID,
            CONF_SOC_ENTITY: SOC,
            CONF_RUNTIME_ENTITY: RUNTIME,
            CONF_STATE_ENTITY: STATE,
            **(options or {}),
        },
        subentries_data=[
            ConfigSubentryData(
                data=data,
                subentry_type=SUBENTRY_PLAYER,
                title=data[CONF_MEDIA_PLAYER].split(".")[1],
                unique_id=data[CONF_MEDIA_PLAYER],
            )
            for data in players
        ],
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
