# Design decisions

Findings from feasibility research, preserved here so they don't only live in chat history.

## Milestone 3 result: full AP round trip confirmed (generate -> server -> client -> item)

Cloned `ArchipelagoMW/Archipelago` as a separate, non-committed dev checkout at
`c:\Users\therm\source\repos\Archipelago-dev` (sibling to this repo, not inside it) --
matches the researched pattern of developing against a full source checkout while only
versioning the isolated world folder. `apworld/ets2ats/` in this repo is that isolated
world; `prototypes/sync_apworld.py` copies it into a checkout's `worlds/` folder for
testing (`py sync_apworld.py <checkout path>`).

Built the smallest possible placeholder world (`apworld/ets2ats/__init__.py`, game name
"ETS2ATS Test", one region, 3 locations, 3 items, no access rules -- not the real game
design, just plumbing validation) and `bridge/ap_client/client.py`, a `CommonContext`
subclass with a manual `/check <location name>` command plus a scripted `--auto-check`
flag (since background/non-interactive processes here can't receive typed stdin commands
after launch).

**Confirmed working end to end**: `Generate.py` produced a multiworld output zip ->
`MultiServer.py` hosted it -> the client connected, authenticated, received the
DataPackage, sent a `LocationChecks` for "Deliver Job A" -> the server filled it and
broadcast the result -> the client's `on_package` handler logged
`RECEIVED ITEM: Money Bundle (from location 1, player 1)`. This is the exact mechanism
Milestone 4 will drive from telemetry events instead of a manual command.

**Three real environment pitfalls hit and fixed, worth remembering**:
1. **Skip the full dependency install.** `ModuleUpdate.py` (imported by every AP script)
   installs the *entire* `requirements.txt` -- including the heavy Kivy GUI stack -- the
   moment it notices anything missing. Setting the environment variable
   `SKIP_REQUIREMENTS_UPDATE=1` bypasses this entirely; install only what's actually needed
   for headless generation/server/client use (colorama, websockets, PyYAML, jinja2, schema,
   typing_extensions, orjson, platformdirs, bsdiff4, certifi, jellyfish, pathspec).
2. **Pin `websockets` to exactly what `requirements.txt` specifies (`==13.1`, `<14`).**
   Installing the latest websockets (17.x) instead broke `MultiServer.py` with
   `'ServerConnection' object has no attribute 'open'` -- newer websockets releases renamed
   that attribute. The repo's own pin exists specifically because of this; don't install
   this dependency unpinned.
3. **Player YAML needs an explicit (even empty) per-game block.** `game: <name>` alone
   isn't enough -- `Generate.py` raises "No game options for selected game" unless the YAML
   also has a top-level `<game name>: {}` section, even when the world defines no custom
   options.

Several other worlds in the monorepo (zillion, sm, soe, ffmq, messenger, osrs,
pokemon_emerald) fail to import due to their own missing optional dependencies
(`requests`, `pyevermizer`, `zilliandomizer`, etc.) -- harmless noise, unrelated to our
world, safe to ignore.

## Milestone 2 result: live telemetry events confirmed working end-to-end

`bridge/telemetry/shared_memory_map.py` is a `ctypes.Structure` mirror of the memory-mapped
struct written by RenCloud/scs-sdk-plugin's `scs-telemetry.dll` (field names/order/types
ported directly from `scs-telemetry/inc/scs-telemetry-common.hpp` in that repo, not
reverse-engineered). Every checked offset (`scs_values`=40, `config_s`=2300,
`gameplay_ll`=4200, `special_b`=4300, `substances`=4400, total size=21600) matches the
source header's own documented zone-boundary comments exactly, confirming no padding
mismatch between the C++ struct and the Python mirror.

**Pitfall hit and resolved**: this machine already had two telemetry-adjacent plugin DLLs
installed (`ETSSharedMemoryMapPlugin64v2.dll`, `TruckyTelemetry.dll`), and it was tempting to
assume one of them was the standard shared-memory plugin. Neither was: string-scanning the
binaries (`py -3.12` + a regex over the raw bytes, no `strings` tool available in this
environment) showed the first is a MOZA sim-racing-wheel hardware plugin using its own
private memory name (`SCSTelemetrySharedv2`), and the second (Trucky) runs an embedded
WebSocket server instead of shared memory at all -- neither exposes `Local\SCSTelemetry`.
Lesson: don't assume an existing plugin matches a target struct/name without verifying via
the binary itself; a filename resembling the expected plugin is not evidence.

We installed RenCloud's actual `scs-telemetry.dll` (release `V.1.12.1`, Win64 build) into
`<ETS2 install>\bin\win_x64\plugins\` (additive -- doesn't touch the other two plugins).
Confirmed via string-scan it references `Local\SCSTelemetry` before installing.

**Also hit**: Python's stdlib `mmap.mmap(-1, size, tagname=...)` on Windows silently
*creates* a fresh zero-filled mapping under that name if one doesn't already exist, rather
than raising -- indistinguishable from "opened successfully" while reading nothing real.
`bridge/telemetry/win_mmf.py` calls the real Win32 `OpenFileMappingW` via ctypes instead,
which fails loudly (`OSError`, "file not found") if the mapping genuinely isn't there --
this is what surfaced the plugin-mismatch problem above in the first place, rather than an
indefinite silent hang.

**Live confirmation** (2026-09-08, real ETS2 session, `bridge/telemetry/smoke_test.py`):
connected with `telemetry_plugin_revision=12` (matches the plugin source's own
`PLUGIN_REVID`), then refueling in-game produced, at the instant it happened:
```
[21:59:59] EVENT refuel: amount=0.0
[22:00:03] EVENT refuelPayed: amount=0.5
```
Job delivered/cancelled/fined/tollgate/ferry/train are read from the same struct
(`gameplay_ll`, `gameplay_s`, `special_b`) via the identical mechanism -- not yet
individually observed live, but there's no remaining reason to expect they'd behave
differently from the confirmed refuel event.

## Milestone 1 result: lossless SII parser/writer, verified against a real save

`bridge/sync/sii_format.py` parses the flat, two-level SII text structure (top-level
`SiiNunit { }` wrapper containing a flat sequence of `type : id { key: value ... }` units,
never nested — cross-references are by id string) into `SiiUnit`/`SiiFile` objects, and
serializes back with `\r\n` line endings matching the game's own formatting exactly.

Verified via `bridge/sync/test_roundtrip.py` against the real "Mod Test" save
(2026-09-08): parsing all 17,118 units and re-serializing with **no edits produces
byte-identical output** to the original decrypted file — strong evidence the parser loses
no information anywhere in a real, full-size save. A targeted edit (`bank.money_account`)
changes exactly one line, confirming field lookup/set is correctly isolated. Live
in-game confirmation wasn't repeated here since Milestone 0 already proved the game
accepts hand-edited plain-text money fields through this exact mechanism (same file
format, same field) — worth a quick live spot-check later once other fields (garages,
trucks, cities) are exercised, but not blocking.

`bridge/sync/sii_crypto.py` is the same AES/zlib decrypt as the `prototypes/` version,
moved here since it's now real (non-throwaway) code; `prototypes/sii_crypto.py` and the
Milestone 0 spike scripts are left as-is for history.

## Reads are live and solid

The official Telemetry SDK exposes job delivered/cancelled, fines, tolls, ferry/train, and
continuous truck/trailer state in real time via shared memory. Multiple mature community tools
(ets2-telemetry-server, LiveSplit auto-splitters) already consume it this way. This is the basis
for live Archipelago location checks.

## Writes are not live, by design, confirmed by SCS staff

An SCS moderator directly answered a forum thread proposing this exact Archipelago integration
with: "mods can't change game settings based on a player event." There is no scripting or
event-trigger layer anywhere in the mod system, no console command for money/unlocks, and the
Input SDK only emulates virtual controller input, not arbitrary actions.

Re-confirmed from several other angles:
- Shop "unlock flag" idea: dead end. World of Trucks reward paint jobs are Steam-account
  entitlements, not save-file state; no SII field for achievement-gated purchasing exists.
- XP/level: same read-only wall as money. `g_exp_gain` is a real cvar but only scales future
  gain rate, it doesn't set a value directly, and it's only settable via `config.cfg` (applies
  next launch), not live.
- No live "cheese" variable exists: every economy-affecting event (fines, tolls, delivery pay)
  is bounded by the game's own formula and can't be arbitrarily set from outside while running.

## The only proven write path: save file + reload

Editing the profile's save file (`game.sii`) while the game is not actively running, picked up
by the player on next load. Proven by existing community tools:
- **TS SaveEditor** — money, player level/skill, garages, trucks/trailers, visited cities,
  custom freight-market jobs.
- **ETS2-ATS-Sync-Helper** — inserts synced freight-market jobs into the save; explicitly
  requires the game closed ("This won't work if you do it with the game running") and the save
  format set to text.

Two additional write surfaces share the same "applies on next load" cadence:
- **Companion mod data** — mods can add entirely new purchasable shop content into existing
  dealers (proven by TruckersMP's own bundled drivable car, purchasable at any dealership). This
  gives us a fully custom, fully-controlled item pool (filler/bonus items) rather than being
  limited to reusing vanilla trucks/garages/cities. Item *prices* are also just a static SII
  field (`price: N`), so a regenerated def-file fragment can implement discount/inflation
  effects the same way.
- **`config.cfg` cvars** — e.g. `g_exp_gain` for temporary XP-rate effects.

## Milestone 0 result: main-menu switching works, no restart needed

**Confirmed empirically on 2026-09-08, against a real profile ("Mod Test") in a real ETS2
install**, contradicting every existing tool's "the game must be closed" advice:

1. **The save file is not OS-locked while at the main menu.** With the game running and backed
   out to the main menu (profile unloaded, process still alive), the save file opened for
   writing without error.
2. **A plain-text save with no `ScsC` encryption wrapper is accepted directly.** ETS2/ATS save
   files are *always* wrapped in an AES-256-CBC + zlib container regardless of `g_save_format`
   (see "Decrypting the save file" below) — `g_save_format "2"` only controls whether the payload
   *inside* that wrapper is text or binary. We wrote a raw `SiiNunit`-prefixed text file with no
   wrapper at all, in place of the real save, and the game loaded it without error or fallback.
3. **The edit persisted through Continue without a process restart.** We set `money_account` to
   a distinctive value (987654321) directly in the save file while the game sat at the main menu
   (process never closed), then clicked Continue on the same profile. The bank balance in-game
   read **987.7M** — the edit took effect live, with no restart of any kind.

This reverses the planned Milestone 4 design: **the primary sync cycle is "return to main menu →
write plain-text save → Continue,"** not "close process → write → relaunch." No `WM_CLOSE`,
no relaunch, no `g_start_in_truck` needed for the common case. The full close/relaunch cycle
(still valid — game autosaves on clean exit) is kept only as a fallback for anything that
genuinely requires a fresh process, e.g. `config.cfg` cvars like `g_exp_gain`, which are only
read at startup.

**Methodology note**: the first attempt at this test looked like a failure — a brand-new profile
resumed into a scripted tutorial mission showing an unrelated intro balance ($2,500), with job
search disabled. That was a test-design flaw, not a real result: tutorials are a walled-off
scripted sequence that doesn't reflect (or was later confirmed to still preserve, once checked
in the actual save file's plain text) the real save state. Grepping the live save file directly
for `money_account` — no decryption needed once files are in text form — showed our edit was
present and untouched, and free-roam later confirmed it was genuinely loaded, not just dormant
on disk. Lesson for future tests: verify against free-roam state (or the raw save content
directly), not a tutorial/scripted-sequence UI.

### Decrypting the save file (needed for reading real saves; not needed for writing)

Save files are unconditionally wrapped in an SCS-proprietary container (magic `ScsC`), even with
`g_save_format "2"`. Algorithm (ported from TheLazyTomcat/SII_Decrypt,
`Source/SII_Decrypt_Decryptor.pas`, MPL-2.0 — that project's own comment attributes the AES key
to a "Savegame Decrypter" utility publicly posted on the SCS forum in 2013, i.e. a long-public,
community-standard constant, not a secret):

- 56-byte header: 4-byte signature (`ScsC`), 32-byte HMAC (unverified/unused on decrypt), 16-byte
  IV, 4-byte decompressed-size field — followed by AES-256-CBC ciphertext.
- Decrypt with the fixed 32-byte key (see `prototypes/sii_crypto.py`) and the header's IV, then
  zlib-decompress the result to get the real SII content (`SiiNunit...` if text).
- Implemented and verified working against a real save in `prototypes/sii_crypto.py`
  (uses `pycryptodome`, added to the environment 2026-09-08).
- **Not needed for the write path** — per the Milestone 0 result above, the game accepts a raw,
  unwrapped plain-text save directly. Decryption is only needed to *read* an existing real save
  (e.g. to find field names, or to preserve a player's actual profile instead of starting fresh).

## UX principle: item application is player-paced

Even though Milestone 0 showed the common case needs only a main-menu round-trip (no process
restart, no capture loss, negligible time cost — much better than originally scoped), the overlay
should still queue received items and let the player trigger "sync" on their own schedule rather
than applying automatically per item. A menu round-trip still interrupts active driving/chat, so
batching remains the right default; it's just a much cheaper interruption than we originally
planned around. The streaming/low-end-hardware concerns that motivated this principle are now
largely moot for the common path (no window close/reopen, no relaunch load time) and only apply
to the rarer fallback case that still needs a full restart (e.g. `config.cfg` cvar changes).

## Environment notes

- Python 3.12 installed via `winget install Python.Python.3.12` on 2026-09-07. On this machine,
  invoke via `py`, not `python` — the bare `python` command resolves to a Windows Store stub
  alias that doesn't dispatch to the real interpreter.
- `g_save_format` set to `"2"` (text-only saves) in the global
  `Documents\Euro Truck Simulator 2\config.cfg` on 2026-09-07 (original backed up alongside as
  `config.cfg.pre-ap-backup`). Only affects saves written *after* the change — existing save
  slots remain in their previous format until next written.
- `g_developer` and `g_console` also set to `"1"` in the same file (2026-09-07) — needed to open
  the in-game developer console at all. Note: editing these while an old game instance is still
  running gets silently clobbered back to `"0"` when that instance later exits and rewrites its
  own config from stale in-memory state — confirm via `Get-Process` that the game isn't running
  before editing, and fully restart (not just reload a profile) before expecting the new values
  to be live, since `config.cfg` is only read at process start.
- `pycryptodome` added to the Python environment on 2026-09-08 for AES-256-CBC support (see
  `prototypes/sii_crypto.py`).
- Test profile "Mod Test" (folder `4D6F642054657374`, hex for "Mod Test") created under
  `Documents\Euro Truck Simulator 2\profiles\` on 2026-09-07 specifically as disposable test
  data — not a real profile, safe to delete/corrupt.
