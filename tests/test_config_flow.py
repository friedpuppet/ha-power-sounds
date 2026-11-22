"""Entry and options flow: the battery inputs come as a set."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.power_sounds.const import (
    CONF_GRID_ENTITY,
    CONF_RUNTIME_ENTITY,
    CONF_SOC_ENTITY,
    CONF_STATE_ENTITY,
    DOMAIN,
)

from .conftest import GRID, RUNTIME, SOC, STATE, make_entry, setup_entry

BATTERY = {CONF_SOC_ENTITY: SOC, CONF_RUNTIME_ENTITY: RUNTIME, CONF_STATE_ENTITY: STATE}


async def test_battery_all_or_none(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, "80", {"device_class": "battery"})
    hass.states.async_set(RUNTIME, "100", {"device_class": "duration"})
    hass.states.async_set(STATE, "idle", {"device_class": "enum"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Звуки", CONF_GRID_ENTITY: GRID, CONF_SOC_ENTITY: SOC}
    )
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "battery_incomplete"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Звуки", CONF_GRID_ENTITY: GRID, **BATTERY}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {CONF_GRID_ENTITY: GRID, **BATTERY}


async def test_grid_only(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "x", CONF_GRID_ENTITY: GRID})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = hass.config_entries.async_get_entry(result["result"].entry_id)
    assert entry.runtime_data.levels is None


async def test_options_reject_a_partial_battery(hass: HomeAssistant) -> None:
    hass.states.async_set(GRID, "on")
    entry = make_entry()
    await setup_entry(hass, entry)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_GRID_ENTITY: GRID, CONF_SOC_ENTITY: SOC, CONF_RUNTIME_ENTITY: RUNTIME}
    )
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "battery_incomplete"}
