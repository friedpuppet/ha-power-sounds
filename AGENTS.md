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
  this one's switch on. Since grid_load_shedding v0.12.0 removed its own (same day) the entities are renamed to the
  old ids: `switch.vitalnia_vlc_telnet_sound_notifications`, `button.vitalnia_vlc_telnet_test_sound_*`. First start took `soc_50` as passed (SOC 40 %).
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

## History (moved from grid_load_shedding's AGENTS.md, 2026-11-22)

Written when the sounds were part of grid_load_shedding; entity ids and versions there are grid_load_shedding's.
The sound files' sources moved here too: `scripts/make_battery_sounds.sh` and `sounds/battery-alpha/`.

- **Sound notifications (v0.4.0, 2026-10-07)**: subentry «VLC-TELNET» on `media_player.vlc_telnet` (VLC add-on
  `core_vlc`, output = analog jack `rk3528-acodec`, a small speaker is plugged in). Sounds (since 2026-10-07)
  `media-source://media_source/local/grid_lost_ostap_6.mp3` / `grid_restored_polina_8.mp3`, the only files in
  `/var/lib/homeassistant/media/`. Each one is a synthesized three-strike bell chime (lost: descending tritone
  dyads, dark; restored: ascending major arpeggio, bright) followed by an edge-tts voice (uk-UA Ostap / Polina,
  rate +10%): «Електрика пропала.» / «Електрика повернулась.». Chime and voice were loudness-matched by EBU R128
  LUFS, but on this small speaker Polina still sounds quieter, so the restored file is deliberately hotter
  (−15.2 vs −19.6 LUFS, peak −0.4 dBFS: no headroom left). The user chose to leave it as is. Volume 80 % (was 50 %, confirmed
  audible), window 11:00–22:00. Entities: `switch.vitalnia_vlc_telnet_sound_notifications`,
  `button.vitalnia_vlc_telnet_test_sound_grid_{lost,restored}`. VLC has no `MEDIA_ANNOUNCE`; the integration
  calls `volume_set` before each `play_media`. `vlc_telnet` sends `volume_level * 500` but aiovlc accepts only 0..499, so 1.0 fails: the announcer caps it at 0.99, and
  a failed `volume_set` no longer stops the sound. Both test sounds confirmed audible. The speaker is powered from
  an inverter-backed outlet, so it keeps working through an outage (except after the battery is empty and the
  inverter has shut down). Not yet heard on a real outage.

- **Battery sounds (v0.5.0, live since 2026-11-03)**: the battery is one percentage entity, an abstraction on purpose
  (the user may pick a phone): no power, capacity or voltage. Live: `sensor.batareia_state_of_charge`, reserve 0 % (until 2026-11-16; now the Deye's SOC, floor = Deye's shutdown SOC since v0.11.0), the six
  `media_source/local/battery_*_ostap.mp3` files (from `sounds/battery-alpha/`) on «VLC-TELNET», battery volume 80 %
  (the grid sounds are also at 80 % now). Entities `sensor.merezha_battery_runtime`,
  `button.vitalnia_vlc_telnet_test_sound_battery_*`. All six test buttons played (VLC at 0.8, no errors) during the
  2026-11-03 outage; not yet heard from a real level crossing.
  - The rate comes from segments of a 1-point fall, not from every state: `battery_soc` updates in ticks, so single 0.1 %
    steps kept the median at 18 %/h with a real 21 %/h.
  - Replay of real history through `BatteryMonitor`, reserve 0 (the user's choice, 2026-11-03): 11-02 gave half 10:59, 2 h
    11:45, quarter 12:18, 1 h 13:08, 10 min 13:20; 10-30 gave half 20:33, 2 h 20:53, quarter 21:48, 10 min 22:01. So 30 min
    (and on 10-30 also 1 h) never played. The battery died with 12–22 % shown, `battery_soc` then jumped to 0, and that jump
    plays only "10 min". The inverter switched off about 10 min after it (13:31, 22:11). Reserve 15 % plays all levels on both days.

