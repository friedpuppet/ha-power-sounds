"""Battery levels: charge and time left, once per discharge, re-armed by a real charge."""

from freezegun.api import FrozenDateTimeFactory

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.power_sounds.const import (
    BATTERY_LEVELS,
    CONF_BATTERY_VOLUME,
    CONF_RUNTIME_ENTITY,
    DOMAIN,
)
from custom_components.power_sounds.levels import LevelTracker

from .conftest import GRID, RUNTIME, SOC, make_entry, setup_entry
from .test_sounds import ANNOUNCEMENT, PLAYER, Player, at

SOUNDS = {
    f"sound_{level}": {"media_content_id": f"media-source://x/{level}.mp3", "media_content_type": "audio/mpeg"}
    for level in BATTERY_LEVELS
}


async def start(hass: HomeAssistant, soc: float, runtime: float | None = None) -> tuple[LevelTracker, list[str]]:
    hass.states.async_set(SOC, str(soc))
    hass.states.async_set(RUNTIME, "unknown" if runtime is None else str(runtime))
    levels: list[str] = []
    tracker = LevelTracker(hass, "e", soc_entity=SOC, runtime_entity=RUNTIME, on_level=levels.append)
    await tracker.async_load()
    tracker.async_start()
    return tracker, levels


async def step(hass: HomeAssistant, soc: float | None = None, runtime: float | str | None = None) -> None:
    if soc is not None:
        hass.states.async_set(SOC, str(soc))
    if runtime is not None:
        hass.states.async_set(RUNTIME, str(runtime))
    await hass.async_block_till_done()


async def discharge(hass: HomeAssistant, soc: float, to: float, minutes_per_percent: float = 3) -> None:
    """Walk the charge down, the time left following it (to 0 %)."""
    while soc > to:
        soc -= 1
        await step(hass, soc, soc * minutes_per_percent)


async def test_each_level_once_in_order(hass: HomeAssistant) -> None:
    tracker, levels = await start(hass, 60, 180)
    await discharge(hass, 60, 1)
    assert levels == ["soc_50", "runtime_120", "soc_25", "runtime_30"]
    tracker.async_stop()


async def test_time_left_alone_crosses(hass: HomeAssistant) -> None:
    """The time left changes every minute, the charge only every few: no need to wait for the charge."""
    tracker, levels = await start(hass, 60, 125)
    await step(hass, runtime=121)
    assert levels == []
    await step(hass, runtime=119)
    assert levels == ["runtime_120"]
    await step(hass, runtime="unknown")  # charging or idle: says nothing
    await step(hass, runtime=110)
    assert levels == ["runtime_120"]
    tracker.async_stop()


async def test_jump_says_only_the_most_urgent(hass: HomeAssistant) -> None:
    tracker, levels = await start(hass, 60)
    await step(hass, 10)
    assert levels == ["soc_25"]
    assert tracker.passed == {"soc_25", "soc_50"}
    await step(hass, runtime=20)
    assert levels == ["soc_25", "runtime_30"]
    assert tracker.passed == set(BATTERY_LEVELS)
    tracker.async_stop()


async def test_charging_is_silent(hass: HomeAssistant) -> None:
    await start(hass, 10)
    tracker, levels = await start(hass, 10)
    for soc in (12, 20, 30):
        await step(hass, soc)
    assert levels == []
    tracker.async_stop()


async def test_first_start_takes_crossed_levels_as_passed(hass: HomeAssistant) -> None:
    tracker, levels = await start(hass, 40, 100)
    assert tracker.passed == {"soc_50", "runtime_120"}
    await step(hass, 39, 95)
    assert levels == []
    tracker.async_stop()


async def test_unavailable_changes_nothing(hass: HomeAssistant) -> None:
    tracker, levels = await start(hass, 51)
    await step(hass, "unavailable")
    assert tracker.soc == 51 and levels == []
    await step(hass, 49.5)
    assert levels == ["soc_50"]
    tracker.async_stop()


async def test_blink_does_not_repeat(hass: HomeAssistant) -> None:
    tracker, levels = await start(hass, 26, 200)
    await step(hass, 24)
    await step(hass, 27)  # charged for a moment
    await step(hass, 24)
    assert levels.count("soc_25") == 1
    tracker.async_stop()


async def test_real_charge_rearms(hass: HomeAssistant) -> None:
    tracker, levels = await start(hass, 60, 180)
    await discharge(hass, 60, 1)
    levels.clear()
    await step(hass, 70, "unknown")
    await discharge(hass, 70, 1)
    assert levels == ["soc_50", "runtime_120", "soc_25", "runtime_30"]
    tracker.async_stop()


async def test_passed_survive_a_restart(hass: HomeAssistant) -> None:
    tracker, levels = await start(hass, 60, 300)
    await discharge(hass, 60, 45, minutes_per_percent=6)
    assert levels == ["soc_50"]
    tracker.async_stop()
    await tracker.async_flush()
    again, levels = await start(hass, 45, 270)
    await discharge(hass, 45, 40, minutes_per_percent=6)
    assert levels == []
    again.async_stop()


async def test_without_a_time_left_sensor(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, "60")
    levels: list[str] = []
    tracker = LevelTracker(hass, "e", soc_entity=SOC, runtime_entity=None, on_level=levels.append)
    await tracker.async_load()
    tracker.async_start()
    assert tracker.levels == ("soc_25", "soc_50")
    await discharge(hass, 60, 1)
    assert levels == ["soc_50", "soc_25"]
    tracker.async_stop()


async def setup(hass: HomeAssistant, soc: float, **options):
    hass.states.async_set(PLAYER, "idle")
    hass.states.async_set(GRID, "on")
    hass.states.async_set(SOC, str(soc))
    hass.states.async_set(RUNTIME, "unknown")
    player = Player(hass)
    entry = make_entry(options=options, players=({**ANNOUNCEMENT, **SOUNDS, CONF_BATTERY_VOLUME: 70},))
    await setup_entry(hass, entry)
    return entry, player


async def test_plays_at_the_battery_volume_with_or_without_grid(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    at(freezer, 14)
    _, player = await setup(hass, 51)
    await step(hass, 49)  # the grid is still on: battery sounds play anyway
    assert player.played == [SOUNDS["sound_soc_50"]["media_content_id"]]
    assert player.calls[0]["service_data"]["volume_level"] == 0.7


async def test_grid_sound_keeps_its_volume(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    at(freezer, 14)
    _, player = await setup(hass, 90)
    hass.states.async_set(GRID, "off")
    await hass.async_block_till_done()
    assert player.calls[0]["service_data"]["volume_level"] == 0.4


async def test_outside_the_window_stays_silent(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    at(freezer, 3)
    entry, player = await setup(hass, 51)
    await step(hass, 49)
    assert player.calls == []
    assert "soc_50" in entry.runtime_data.levels.passed


async def test_test_buttons(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    at(freezer, 3)
    entry, player = await setup(hass, 90)
    sub_id = next(iter(entry.subentries))
    reg = er.async_get(hass)
    for level in BATTERY_LEVELS:
        button = reg.async_get_entity_id("button", DOMAIN, f"{sub_id}_test_sound_{level}")
        await hass.services.async_call("button", "press", {ATTR_ENTITY_ID: button}, blocking=True)
    assert player.played == [SOUNDS[f"sound_{level}"]["media_content_id"] for level in BATTERY_LEVELS]
    assert all(c["service_data"]["volume_level"] == 0.7 for c in player.calls if c["service"] == "volume_set")


async def test_no_time_left_buttons_without_the_sensor(hass: HomeAssistant) -> None:
    entry, _ = await setup(hass, 90, **{CONF_RUNTIME_ENTITY: None})
    sub_id = next(iter(entry.subentries))
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("button", DOMAIN, f"{sub_id}_test_sound_soc_50")
    assert not reg.async_get_entity_id("button", DOMAIN, f"{sub_id}_test_sound_runtime_30")


async def test_only_while_discharging_with_a_state_entity(hass: HomeAssistant) -> None:
    state = "sensor.battery_state"
    hass.states.async_set(SOC, "51")
    hass.states.async_set(state, "idle")
    levels: list[str] = []
    tracker = LevelTracker(
        hass, "e", soc_entity=SOC, runtime_entity=RUNTIME, on_level=levels.append, state_entity=state
    )
    await tracker.async_load()
    tracker.async_start()
    await step(hass, 49.9)  # an idle battery's charge jitters: nothing
    assert levels == []
    hass.states.async_set(state, "discharging")  # a real discharge starts below the level: said now
    await hass.async_block_till_done()
    assert levels == ["soc_50"]
    await step(hass, 30, 100)
    assert levels == ["soc_50", "runtime_120"]
    hass.states.async_set(state, "charging")
    await step(hass, 24)
    assert levels == ["soc_50", "runtime_120"]
    tracker.async_stop()
