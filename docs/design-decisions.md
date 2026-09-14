# Design decisions

Findings from feasibility research, preserved here so they don't only live in chat history.

## Reliability bug: telemetry silently reading a dead mapping after a game restart

Caught during Milestone 6 live testing. A player delivered a job (including a ferry leg) that
never registered as a check -- `telemetry_watcher` had silently stopped detecting anything.
Root cause: the game process had been closed and relaunched partway through the test session
(confirmed via `Get-Process`: the client had been running since 14:05, the game's current
process had a start time of 16:53). Windows keeps a named shared memory mapping's data alive
for as long as *any* process still holds a handle/view to it -- including ours -- even after
the process that originally created it (the game) exits. `telemetry_watcher` only ever
attempts to (re)attach when it doesn't currently hold a handle at all, so once it successfully
attached once, it never re-validated that the mapping was still the *live* one. The result: a
frozen snapshot read forever, silently, with no error to signal it -- the exact kind of bug
that's invisible until someone happens to close/reopen the game mid-session.

Fixed by tracking the top-level `time` field (confirmed via the SDK: a continuously-advancing
telemetry clock) and reattaching if it stalls for too long. First attempt used a 3-second
threshold and immediately produced a false-positive storm: `time` legitimately stops advancing
while sitting at the main menu with no profile loaded (no simulation running to tick it), so
the short threshold just churned on an otherwise-still-valid mapping. Widened to ~60 seconds --
still far shorter than the hours-long freeze the real bug produced, but well clear of normal
menu-idle time. Reattaching on a false positive is cheap and harmless (the mapping is still
valid, so it just reopens the same handle), so erring toward a slightly generous threshold
costs nothing.

## Milestone 5 result: tray + overlay + dashboard, launched via the AP ecosystem itself

Built `bridge/overlay/` (tray icon, transparent corner-notification window, dashboard popup)
per the plan settled in the roadmap update below, and wired it into `bridge/ap_client/
client.py` alongside the existing telemetry watcher. Also registered the client as an
Archipelago Launcher `Component` (`apworld/ets2ats/__init__.py`) so it appears as "ETS2ATS
Client" in the same Launcher app used for any other AP game -- no command line needed. Also
implemented the very first architecture idea raised for this whole project:
`bridge/sync/profile_paths.py` matches the AP slot name to the ETS2/ATS profile name
(profile folders are the uppercase hex of their UTF-8 display name, confirmed against real
profiles) to auto-locate the save for Sync Now, falling back to "most recently modified save
across all profiles" with a warning when no profile matches.

**Two real bugs caught during testing, both worth remembering**:
1. **`ctx.ui` collides with a name CommonContext already reserves.** Assigning our overlay
   object to `Ets2AtsContext.ui` silently replaced CommonContext's own (normally `None`,
   since we never call `run_gui()`) reference to its Kivy-based GUI object. This produced no
   error until `CommonClient.py`'s `server_loop` actually hit its reconnect path and called
   `ctx.ui.update_address_bar(...)`, crashing with `AttributeError: 'UI' object has no
   attribute 'update_address_bar'` -- a latent bug that only surfaces on connection loss, not
   on the happy path. Fixed by renaming ours to `ctx.tracker_ui`. Lesson: don't assume an
   attribute name is free just because the base class doesn't document it -- check for it
   directly (`grep self\.<name>` in the base class) before adding new state to a subclass of
   a large, actively-used framework class.
2. **The tray's Quit option never told the owning app to quit.** `UI`'s internal "quit" event
   handler tore down its own Tk mainloop and tray icon but never called the `on_quit`
   callback passed in from outside -- caught by a standalone test asserting Quit produced a
   `'quit'` event, which it didn't (`events captured: ['sync']`, no `'quit'`). Uncaught, this
   would have left the AP connection and telemetry watcher running invisibly forever after a
   player thought they'd quit. Fixed by calling `self._on_quit()` in the quit branch before
   tearing down the UI thread.

**Confirmed working end to end**, via the actual Launcher component invocation path (not a
shortcut around it): `comp.run('--connect', ..., '--name', 'Tester')` -- matching exactly
what `ArchipelagoLauncher.exe "ETS2ATS Client"` would do -- connected cleanly, the tray icon
and dashboard came up, and clicking "Sync Now" from the tray correctly fell back to "most
recently modified save" (since the test slot name "Tester" doesn't match the real profile
name "Mod Test") and applied a real queued item to the real save
(`987563840 -> 987613840`). Directly verified the primary (non-fallback) path separately:
`find_profile_save("ets2", "Mod Test")` resolves straight to the same real save file with no
warning, confirming slot-name-matches-profile-name sync works as designed.

**Known limitation, not a bug**: the transparent overlay window requires Borderless Windowed
mode to be visible over the game (see roadmap notes below) -- not exercised in this test
session since no game was running; the tray icon and dashboard don't have that limitation
since they aren't drawn over the game's surface.

### Follow-up: confirm before touching a guessed save file

User-suggested safety fix after the above testing: the fallback path (no profile name
matches the slot name) was applying items to "the most recently modified save" immediately,
with only a log message -- silently correct in testing because the fallback happened to
guess right, but there's nothing stopping it from guessing a *different* real profile's save
on a machine with more than one. Changed `perform_sync` to require an explicit yes via a new
`UI.confirm()` before ever writing through the fallback path; the exact profile-name match
still applies with no prompt, since that path is exactly what the player set up on purpose.

**One more dialog-visibility bug caught while verifying the fix**: the first implementation
used `tkinter.messagebox.askyesno`, which never became visible in testing -- it's parented to
`ui.py`'s root window, which stays permanently withdrawn (it only exists to anchor the
mainloop), and a messagebox attached to a withdrawn parent did not reliably raise itself
above other windows on Windows. Fixed by building a plain `Toplevel` instead
(`bridge/overlay/confirm_dialog.py`), the same way the already-confirmed-working overlay
notification window is built: explicit `-topmost`, plus `lift()`/`focus_force()` before
blocking on `wait_window()`. Confirmed visible and answerable end to end afterward.

## Future work: auto-launch the game from the Launcher click

Raised while investigating the stale-telemetry bug above: could launching ETS2/ATS ourselves
(from `launch_client`, alongside starting the AP client/tray/overlay) and tracking that
specific process's PID solve the reliability issue more precisely? Evaluated and set aside for
now -- worth recording why, so it isn't re-litigated from scratch later:

- **Doesn't meaningfully improve the reliability fix.** Tracking a known PID would let us
  detect the game closing *instantly* instead of within the ~60s heartbeat-staleness window
  above, but the recovery step is identical either way (close the handle, reattach to whatever
  mapping is currently live) -- shaving a worst-case minute off detection time for a background
  check-detector isn't worth the added complexity. It also wouldn't fully generalize: if the
  player closes the game and relaunches it themselves rather than through us, we have no PID
  to track regardless of whether we launched the first instance.
- **The real value would be a different goal**: making the Milestone 5 "one click starts
  everything" experience include the game itself, not just the AP client/tray/overlay. That's
  a legitimate, separate feature -- but it needs real scoping of its own before attempting:
  finding the correct install path (Steam vs. non-Steam, default vs. custom install
  location), picking ETS2 vs. ATS, and choosing a launch method (`steam://rungameid/...` vs.
  the exe directly). Deferred to a later milestone, to be scoped on its own rather than as a
  side effect of the telemetry bug fix.

## Milestone roadmap update (post-Milestone 4)

Scoping pass for milestones 5-7 after Milestone 4's live confirmation. Two changes from the
original build plan (`docs` didn't exist yet when that plan was written, so recording the
change here):

**Reordered 6 and 7.** Originally: overlay (5) -> content mod (6) -> full apworld design (7).
Now: overlay (5) -> full apworld design (6) -> content mod (7). Reasoning: the content mod's
job is to supply whatever shop items the real game design (garage/truck/part unlocks, etc.)
decides it needs -- building it first meant guessing at an item list before the design that
determines it exists. Design first, then author content to match.

**Milestone 6 (full apworld design) scope: broad, not narrow.** Chosen over a
deliveries-and-money-only first pass -- the full original vision (deliveries, city discovery,
garage/truck/part unlocks, XP-rate boosts via `g_exp_gain`, fines-as-traps, ETS2/ATS/both
options) is the target for the first real design, accepting more upfront design work in
exchange for matching the original ambition rather than needing a second design pass later.

**Milestone 5 (overlay/tracker UI) notification approach**, settled after working through the
actual constraints:
- Native OS toast notifications (the obvious first idea) are undermined by Windows Focus
  Assist / Game Mode, which routinely suppresses toasts specifically while a game has focus --
  exactly the moment this needs to notify the player.
- A true in-game overlay (rendered inside the game's own frame, like ReShade/Special
  K/Discord's overlay) requires DLL injection and hooking the game's DirectX `Present()` call.
  This is a substantial standalone technical effort, out of proportion to what Milestone 5
  needs to ship -- flagged as a possible future enhancement, not committed to now.
- **Chosen approach**: a transparent, click-through, always-on-top desktop window drawn in a
  screen corner. No process injection -- it's just a normal win32 layered window
  (`WS_EX_LAYERED` + `WS_EX_TRANSPARENT` + topmost) that visually sits on top of the game via
  the desktop compositor. This works as long as the game runs in **Borderless Windowed** mode
  (already our standing recommendation for streaming, per Milestone 4-era discussion) but is
  invisible in true exclusive Fullscreen mode, where the desktop compositor is bypassed
  entirely. A toast notification is kept as a best-effort fallback for exclusive-fullscreen
  players (better than nothing, even if Focus Assist sometimes eats it).
- Stack: `pystray` (background tray icon + right-click menu), the transparent overlay window
  for in-corner alerts, a small `tkinter` popup (opened from the tray icon) for the dashboard
  (connection status, live check feed, pending item count, manual Sync button). Chosen over
  PySide6/Qt specifically to stay dependency-light and avoid a second, heavier window
  competing with the game for focus/rendering -- matches the low-end-hardware/streaming
  concerns raised early in this project's design discussion.

## Milestone 4 result: real telemetry-driven checks + save-file item sync confirmed

Replaced the Milestone 3 placeholder world with a still-small but *real* slice: three
`Delivery #N` locations that check off actual `special_b.jobDelivered` rising edges from
live SCS telemetry (bridge/telemetry/), and three money-bundle items applied to a real
save's `bank.money_account` field via the exact mechanism Milestone 0/1 proved safe
(bridge/sync/apply_items.py). Renamed the world from "ETS2ATS Test" to "ETS2ATS" to mark
the shift away from pure plumbing -- still not the full Milestone 7 design (one flat
region, no access rules), but no longer fake data either.

Chose money over a truck-part/vehicle-unlock item for this milestone deliberately: money
edits are the mechanism already proven end-to-end, while vehicle ownership lives in save
structures (garage/dealer records) we haven't mapped yet. Using an unproven mechanism here
would have made this milestone a bad test of the wiring itself.

`bridge/ap_client/client.py`'s `telemetry_watcher` coroutine runs alongside the existing
AP network loop: it attaches to the SCS shared memory (retrying every 5s if the game/plugin
isn't up yet, since that must never crash the client), edge-detects `jobDelivered`, and
maps each successive delivery to the next `Delivery #N` location via `check_locations`.
Received items are queued (and persisted to `pending_items.json`, so a client restart
doesn't lose them) rather than applied immediately -- the player runs the new `/sync <path
to game.sii>` command once they're back at the main menu, which sums the queued items'
money values and calls `apply_money_delta`.

**Confirmed working**:
- `Generate.py` accepted the real slice (3 locations, 3 items) without error.
- A local `MultiServer.py` + the updated client reproduced the same connect/auth flow
  proven in Milestone 3 (the network mechanism itself didn't change, only what triggers a
  check and what happens on receipt).
- The client survives telemetry being unavailable (game not running) without crashing --
  `telemetry_watcher` just retries silently, confirmed by leaving the client connected
  with no game running.
- `apply_money_delta` was verified directly against a synthetic save: given
  `money_account: 500000` and a simulated 35,000 total from two queued items, it correctly
  wrote `money_account: 535000`, left everything else in the file untouched, and created a
  timestamped backup before writing.

**Live confirmation (real game, real save)**: delivered a real job on the Mod Test
profile -- `telemetry_watcher` logged `jobDelivered -> checking 'Delivery #1'
(revenue=1832)`, the server filled it and handed back `50,000 Bundle`, and the client
queued it (`RECEIVED ITEM: 50,000 Bundle ... -- queued, run /sync to apply`). Other
telemetry events fired during the same session (fines, job start, a discovered city) were
correctly ignored -- only `jobDelivered` drives a check, as designed. After backing out to
the main menu (autosave confirmed via the freshly-rewritten `save/autosave/game.sii`),
applying the queued item brought `money_account` from `987513840` to `987563840` -- a
+50,000 delta wrote correctly -- and the in-game balance after clicking Continue matched
exactly. This closes out the one thing Milestone 4 hadn't yet proven live: telemetry
detection and the save-file sync both work against the real game, not just synthetic
tests.

One clarification that came up during the live test, worth keeping: the main-menu
requirement only applies to the *write* side (applying queued items to the save).
Telemetry-driven check detection is read-only and has no such restriction -- checks fire
instantly during live gameplay, exactly per the hybrid notification/deferred-effect UX
already chosen; only the deferred item application needs to wait for a safe moment.

**One environment pitfall hit**: running `client.py` by absolute path from inside the
Archipelago checkout directory (`cd checkout && py <path>\client.py`) still failed with
`ModuleNotFoundError: No module named 'ModuleUpdate'` -- Python sets `sys.path[0]` to the
*script's own* directory when invoked by path, not the process's cwd, so being "in" the
checkout directory doesn't help. Fixed by setting `PYTHONPATH` to the checkout root
explicitly rather than relying on cwd.

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
