# archipelago-ets2ats

A bridge/mod that lets Euro Truck Simulator 2 and American Truck Simulator be played as an
[Archipelago](https://archipelago.gg) multiworld randomizer game.

## Status

Early prototyping. See [docs/design-decisions.md](docs/design-decisions.md) for the architecture
and the feasibility research behind it, and the build plan for the current milestone.

## Why this shape

SCS's mod/SDK ecosystem is read-heavy and write-light: live game state (jobs, fines, position)
is readable via the official Telemetry SDK, but there is no scripting or event-trigger layer, so
nothing can be granted into a running game session. The only proven way to change money, unlocks,
XP, or shop content is editing the profile's save file (and companion mod data / `config.cfg`)
while the game isn't actively running, applied on the next reload. The design embraces this:
checks are detected and shown live, items are queued and applied in player-paced batches.

## Repo layout

- `apworld/` — the Archipelago World definition (Python)
- `bridge/` — the standalone bridge process (telemetry reader, AP client, save/mod-data writer,
  restart automation, overlay UI)
- `content-mod/` — companion `.scs` mod source supplying AP-exclusive shop items
- `prototypes/` — throwaway spike scripts, not shipped
- `docs/` — design notes

## Requirements

- Python 3.11.9–3.13 (matches Archipelago's supported range). On this machine, invoke via `py`,
  not `python` (the bare `python` command resolves to the Windows Store stub alias).
