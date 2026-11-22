# Power Sounds

Home Assistant integration: play sounds on media players when the grid is lost or comes back, and when the battery
crosses a level (half or quarter charge, 2 hours or 30 minutes left). The battery side works with
[Battery Monitor](https://github.com/friedpuppet/ha-battery-monitor)'s sensors.

## Options (the inputs)

- **Grid** (optional): a binary sensor, on while the flat runs from the grid. Grid lost = on → off, restored =
  off → on. Unavailable or unknown in between (e.g. an inverter out of sight) says nothing.
- **Battery** (optional, all three or none):
  - **Battery charge**: the charge in % that Battery Monitor works from, for the half and quarter charge levels.
  - **Battery time left**: Battery Monitor's Time left, for the 2 hours and 30 minutes levels.
  - **Battery state**: Battery Monitor's State. The levels are checked only while it is `discharging`: a jitter of
    an idle battery's charge says nothing, and a level crossed meanwhile is said when the discharge starts.

## Players

Each media player is a subentry («Add player»): sounds for grid lost / restored and for each battery level (all
optional; without a sound the event isn't announced), **Volume** for the grid sounds and **Battery sounds volume**,
a **window** (default 11:00–22:00, may cross midnight; clear both times to play at any time) and an on/off flag,
also a switch on the player's device. Upload your own audio files in Media → Local media. The volume is set on the
player right before each sound (capped at 99 %, since vlc_telnet rejects 100 %).

## Battery levels

- **Half / quarter charge**: the charge falls below 50 % / 25 %.
- **2 hours / 30 minutes left**: the time left is at or under 120 / 30 minutes; checked on every change of the
  time-left sensor, not only when the charge changes.
- Each level plays once per discharge, with or without the grid. A level comes back after 5 points of real charging,
  so a short blink repeats nothing. If several are crossed together, only the most urgent plays. A level crossed
  outside the window is skipped, not delayed. The passed levels survive a restart; on the very first start the
  levels already crossed are taken as passed, silently.

## Entities (on each player's device)

| Entity | Purpose |
|---|---|
| `switch.<player>_sound_notifications` | The player's on/off flag. Attributes `window_start` / `window_end`. |
| `button.<player>_test_sound_<event>` | Play that sound now, ignoring the window and the switch. One per grid event (with a grid sensor) and battery level (with the battery sensors). |

## Development

```sh
uv sync
uv run pytest -q
```
