"""Config, options and player subentry flows for Power Sounds."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    BATTERY_INPUTS,
    BATTERY_LEVELS,
    CONF_BATTERY_VOLUME,
    CONF_ENABLED,
    CONF_GRID_ENTITY,
    CONF_MEDIA_PLAYER,
    CONF_RUNTIME_ENTITY,
    CONF_SOC_ENTITY,
    CONF_STATE_ENTITY,
    CONF_SOUND_LOST,
    CONF_SOUND_RESTORED,
    CONF_VOLUME,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_VOLUME,
    DEFAULT_WINDOW,
    DOMAIN,
    SUBENTRY_PLAYER,
)


def _suggested(defaults: dict[str, Any], key: str) -> dict | None:
    return {"suggested_value": defaults[key]} if defaults.get(key) else None


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_GRID_ENTITY, description=_suggested(defaults, CONF_GRID_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Optional(CONF_SOC_ENTITY, description=_suggested(defaults, CONF_SOC_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.BATTERY)
            ),
            vol.Optional(
                CONF_RUNTIME_ENTITY, description=_suggested(defaults, CONF_RUNTIME_ENTITY)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.DURATION)),
            vol.Optional(CONF_STATE_ENTITY, description=_suggested(defaults, CONF_STATE_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.ENUM)
            ),
        }
    )


def _battery_errors(user_input: dict[str, Any]) -> dict[str, str]:
    """The battery inputs come as a set: all three or none."""
    given = [bool(user_input.get(key)) for key in BATTERY_INPUTS]
    return {"base": "battery_incomplete"} if any(given) and not all(given) else {}


class PowerSoundsConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry per set of inputs (grid, battery); players are subentries."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and not (errors := _battery_errors(user_input)):
            options = dict(user_input)
            name = options.pop(CONF_NAME)
            return self.async_create_entry(title=name, data={}, options=options)
        defaults = user_input or {}
        schema = vol.Schema(
            {vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Power sounds")): selector.TextSelector()}
        ).extend(_options_schema(defaults).schema)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PowerSoundsOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_PLAYER: PlayerSubentryFlow}


class PowerSoundsOptionsFlow(OptionsFlow):
    """Change the input entities (the entry reloads afterwards)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and not (errors := _battery_errors(user_input)):
            return self.async_create_entry(data=user_input)
        defaults = user_input or dict(self.config_entry.options)
        return self.async_show_form(step_id="init", data_schema=_options_schema(defaults), errors=errors)


_BATTERY_SOUNDS = tuple(f"sound_{level}" for level in reversed(BATTERY_LEVELS))


def _player_schema(defaults: dict[str, Any]) -> dict:
    """Sounds, volumes, window and the on/off flag of a player."""
    sound = selector.MediaSelector(selector.MediaSelectorConfig(accept=["audio/*"]))
    volume = selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.SLIDER)
    )
    return {
        vol.Optional(CONF_SOUND_LOST, description=_suggested(defaults, CONF_SOUND_LOST)): sound,
        vol.Optional(CONF_SOUND_RESTORED, description=_suggested(defaults, CONF_SOUND_RESTORED)): sound,
        vol.Required(CONF_VOLUME, default=defaults.get(CONF_VOLUME, DEFAULT_VOLUME)): volume,
        **{vol.Optional(key, description=_suggested(defaults, key)): sound for key in _BATTERY_SOUNDS},
        vol.Required(CONF_BATTERY_VOLUME, default=defaults.get(CONF_BATTERY_VOLUME, DEFAULT_VOLUME)): volume,
        vol.Optional(CONF_WINDOW_START, description={"suggested_value": defaults.get(CONF_WINDOW_START)}): selector.TimeSelector(),
        vol.Optional(CONF_WINDOW_END, description={"suggested_value": defaults.get(CONF_WINDOW_END)}): selector.TimeSelector(),
        vol.Required(CONF_ENABLED, default=defaults.get(CONF_ENABLED, True)): selector.BooleanSelector(),
    }


def _player_data(user_input: dict[str, Any], errors: dict[str, str]) -> dict[str, Any]:
    data: dict[str, Any] = {
        CONF_VOLUME: user_input.get(CONF_VOLUME, DEFAULT_VOLUME),
        CONF_BATTERY_VOLUME: user_input.get(CONF_BATTERY_VOLUME, DEFAULT_VOLUME),
        CONF_ENABLED: user_input.get(CONF_ENABLED, True),
    }
    start, end = user_input.get(CONF_WINDOW_START), user_input.get(CONF_WINDOW_END)
    if start or end:
        if not start or not end:
            errors["base"] = "window_incomplete"
        elif start == end:
            errors["base"] = "window_empty"
        data |= {CONF_WINDOW_START: start, CONF_WINDOW_END: end}
    for key in (CONF_SOUND_LOST, CONF_SOUND_RESTORED, *_BATTERY_SOUNDS):
        if sound := user_input.get(key):
            data[key] = {k: sound[k] for k in ("media_content_id", "media_content_type")}
    return data


class PlayerSubentryFlow(ConfigSubentryFlow):
    """A media player that plays the sounds."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        ent_reg = er.async_get(self.hass)
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_MEDIA_PLAYER]
            reg_entry = ent_reg.async_get(entity_id)
            ref = reg_entry.id if reg_entry else entity_id
            data = _player_data(user_input, errors)
            if any(s.unique_id == ref for s in entry.subentries.values()):
                errors[CONF_MEDIA_PLAYER] = "already_configured"
            if not errors:
                state = self.hass.states.get(entity_id)
                title = (state.name if state else None) or entity_id
                return self.async_create_entry(title=title, data={CONF_MEDIA_PLAYER: ref, **data}, unique_id=ref)

        existing = [
            entity_id
            for s in entry.subentries.values()
            if (entity_id := er.async_resolve_entity_id(ent_reg, s.data[CONF_MEDIA_PLAYER]))
        ]
        start, end = DEFAULT_WINDOW
        defaults = user_input or {CONF_WINDOW_START: start, CONF_WINDOW_END: end}
        schema = vol.Schema(
            {
                vol.Required(CONF_MEDIA_PLAYER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="media_player", exclude_entities=existing)
                ),
                **_player_schema(defaults),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Change sounds, volumes, window (clear both times for "always") and the on/off flag."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _player_data(user_input, errors)
            if not errors:
                return self.async_update_and_abort(
                    self._get_entry(), subentry, data={CONF_MEDIA_PLAYER: subentry.data[CONF_MEDIA_PLAYER], **data}
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(_player_schema(user_input or dict(subentry.data))),
            errors=errors,
            description_placeholders={"player": subentry.title},
        )
