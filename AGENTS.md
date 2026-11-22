# power-sounds — Home Assistant integration

Subproject of `homeassistant` (see `../AGENTS.md`). Custom integration **`power_sounds`**: sounds on grid loss and
return and on battery levels. Step 2 of the split in `../battery-split-plan.md` (2026-11-22, the user's option A):
`announcer.py`, the announcement subentries and the test buttons moved here from `grid_load_shedding`, and the level
logic (`passed`, re-arm, crossings) from its `battery.py`. README has the rules and the entities.

## Status

- v0.1.0 written 2026-11-22, tests green (`uv run pytest`, PHCC pinned = HA 2026.8.3). Not published yet: waits for
  the repo `friedpuppet/ha-power-sounds` (the user creates repos and adds them to the PAT
  `~/.config/github/token-grid-load-shedding`).
- Planned live entry: grid `binary_sensor.e_elektrika`, charge `sensor.vkhidna_zona_deye_inverter_battery`, time left
  `sensor.monitor_batarei_time_left` (battery_monitor); player subentry `media_player.vlc_telnet` with
  grid_load_shedding's «VLC-TELNET» settings (files, volumes, window 11:00–22:00). Enable it and disable
  grid_load_shedding's announcement subentry in the same step: never two sound sources at once.
- Same conventions as `../grid-load-shedding/`. The brand icon is a copy of grid_load_shedding's for now.

## Differences from grid_load_shedding's sounds (on purpose)

- The grid comes from a binary sensor's state, not from `GridMonitor`: only a direct on → off / off → on counts, as
  before (`GridMonitor` also gave `None` for unknown, which never announced).
- Time-left levels are checked on every change of the time-left sensor (battery_monitor updates it every minute), not
  only when the charge falls; an unknown time left clears the last value, so a stale estimate can't fire after a
  charge (found by the tests).
- First start: levels already crossed count as passed, so installing mid-discharge says nothing.
- A charge jump that also crosses a time-left level gives two sounds now (two sensors, two events), not one.

## Layout

| Path | What |
|---|---|
| `custom_components/power_sounds/announcer.py` | `Announcer` (grid binary sensor → lost/restored, window, switch, volume, play) and `Player`. |
| `.../levels.py` | `LevelTracker`: charge and time-left levels, persisted `passed` / `low` (`Store` `power_sounds.<entry_id>.levels`). |
| `.../config_flow.py` | Entry flow (inputs), options flow, `player` subentry flow. |
| `.../switch.py` `button.py` | Per-player switch and test buttons, on the player's device. |
| `tests/test_sounds.py` | Grid sounds, window, switch, flows. |
| `tests/test_levels.py` | Battery levels and their sounds. |
