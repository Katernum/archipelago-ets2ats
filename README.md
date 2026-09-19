# archipelago-ets2ats

A bridge/mod that lets Euro Truck Simulator 2 and American Truck Simulator be played as an
[Archipelago](https://archipelago.gg) multiworld randomizer game.

## Why Claude

Thanks to my wonderful college and work, I'm highly trained in the world of C, RedShift, and 
all the fun things associated. Python was not one of the things they put much care into. As such,
most of the build needs to be written by someone that knows the deep intricacies of python. And
since my work involves testing Claude architecture, and I get copious amounts of free tokens, we're
going to see how different prompt designs create codebases on Sonnet 5 High. I know enough to be able
to troubleshoot the code and write a decent chunk myself, but I'm using this as an excuse to do work
as well as not setting my ETS on fire.

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

- `apworld/ets2ats/` — the Archipelago World definition (Python), including:
  - `apworld/ets2ats/bridge/` — the standalone bridge process (telemetry reader, AP client,
    save/mod-data writer, overlay UI). Lives inside the world package itself (not a sibling
    folder) so it ships inside the real packaged `.apworld` — see docs/design-decisions.md.
- `content-mod/` — companion `.scs` mod source supplying always-purchasable cosmetic content
- `prototypes/` — throwaway spike scripts, not shipped
- `docs/` — design notes

## Requirements

- Python 3.11.9–3.13 (matches Archipelago's supported range). On this machine, invoke via `py`,
  not `python` (the bare `python` command resolves to the Windows Store stub alias).
- `pip install -r requirements.txt` for `bridge/`'s own dependencies (save-file crypto,
  telemetry, tray/overlay UI). Running the client directly (outside the Archipelago Launcher)
  also needs a separate Archipelago installation/checkout, and since `bridge/` is a nested
  package now, it must be run as a module, not a bare script:
  `py -m worlds.ets2ats.bridge.ap_client.client --connect ...` — see docs/design-decisions.md.
