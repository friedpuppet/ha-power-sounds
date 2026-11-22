# power-sounds — Home Assistant integration

Subproject of `homeassistant` (see `../AGENTS.md`). Custom integration **`power_sounds`**: sounds on grid loss and
return and on battery levels. Step 2 of the split in `../battery-split-plan.md` (2026-11-22, the user's option A):
`announcer.py`, the announcement subentries and the test buttons moved here from `grid_load_shedding`, and the level
logic (`passed`, re-arm, crossings) from its `battery.py`. README has the rules and the entities.

## Status

- **v0.1.0 released and live 2026-11-22.** Repo **[friedpuppet/ha-power-sounds](https://github.com/friedpuppet/ha-power-sounds)**
  (public, created by the user), pushed and released with the PAT `~/.config/github/token-grid-load-shedding`
  (same push command as `../battery-monitor/AGENTS.md`). Marketplace repo id **`1467926077`**; first install needed
  no restart, updates do (WS `marketplace/repository/install`).
- Live entry **«Звуки»** `01M82DHM37NWYZ4651FRTXRJ5C`: grid `binary_sensor.e_elektrika`, charge
  `sensor.vkhidna_zona_deye_inverter_battery`, time left `sensor.monitor_batarei_time_left` (battery_monitor). Player
  subentry `media_player.vlc_telnet` with grid_load_shedding's «VLC-TELNET» settings: grid_lost_ostap_6.mp3 /
  grid_restored_polina_8.mp3 at 80 %, battery_soc_50/25 and battery_runtime_120/30 (`_ostap.mp3`) at 60 %, window
  11:00–22:00 (the old subentry's leftover `sound_runtime_60` / `_10` were not copied: no such levels since v0.6.0).
  Switched over 2026-11-22 22:01 Kyiv: grid_load_shedding's `switch.vitalnia_vlc_telnet_sound_notifications` off,
  this one's `switch.vitalnia_vlc_telnet_sound_notifications_2` on. The new entities carry a `_2` suffix until
  grid_load_shedding's are removed (plan step 4); rename them then. First start took `soc_50` as passed (SOC 40 %).
  Not yet heard: a test button or a real event (switched over after the window closed).
- v0.1.1 (2026-11-22, the user's question «why not the monitor's state?»): optional Battery state entity; live
  `sensor.monitor_batarei_state`, so the levels count only while discharging.
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
