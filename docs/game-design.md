# Milestone 6 game design

The real location/item/rules design, scoped after Milestone 5. Distinct from
`docs/design-decisions.md` (technical findings/pitfalls) -- this is the actual game spec,
grounded in real fields found in a live save file (see "Save-file findings" below) rather
than assumption.

**Implemented and confirmed working** (see "Implementation notes" at the bottom for what was
actually built and two real bugs caught along the way) via a full generate -> host -> connect
round trip against the real Mod Test profile's save: the save-poller correctly detected all 4
pre-existing visited cities and 3 pre-existing dealer unlocks on first connect, sent real
checks for each, received a real mix of Money Bundle/XP Grant items back, and `apply_deltas`
correctly applied a combined money+XP sync in one pass. A real live delivery then confirmed
the telemetry-driven side too: `Delivery #1` fired correctly (215km, 0% damage) and money from
the actual in-game payout appeared in the save independent of anything AP-granted. Not yet
confirmed live: distance milestones (no delivery so far has crossed the 500km first
threshold) or any of the four goal types.

**`g_exp_gain` suppression confirmed working, with a notable side effect worth recording**:
isolating just that one delivery's own contribution (XP immediately before minus immediately
after, with no Sync in between), it added only +235 XP naturally -- consistent with heavy
suppression at `g_exp_gain "0.01"`. Separately, two Syncs
in the same session applied a combined +5,000 XP from AP items, taking total XP to 5,815 and
granting 6 skill points at once. This is expected, not a bug: ETS2 recalculates level/skill
points from total `experience_points` regardless of source, and early levels need
comparatively little XP each, so a concentrated lump-sum grant crossing several thresholds at
once is the natural result of suppressing the slow/steady natural path in favor of AP grants
-- exactly the intended effect (natural play alone can no longer reliably level up a
character; reaching hazmat/long-haul/just-in-time cargo access now depends on receiving
checks from other players, not solo grinding).

## Core structure

- **Locations** (checks): things *this player* does in their own game. Checking one sends an
  item to another player in the multiworld.
- **Items** (received): things *other players'* progress sends to this player -- resources or
  traps applied to this player's save via Sync.

This mirrors how deliveries already work (Milestone 4): the player's own progress generates
checks; other worlds' progress sends money. Everything below extends that same shape rather
than introducing a different one.

## Locations

| Location | Detection | Mechanism |
|---|---|---|
| Delivery #N | Live telemetry | `special_b.jobDelivered` rising edge (proven, Milestone 4) |
| City Discovered: `<city>` | Save-file poll | New entry appears in `economy.visited_cities` |
| Dealer Unlocked: `<city>` | Save-file poll | New entry appears in `economy.unlocked_dealers` -- confirmed distinct from city discovery: dealers unlock by driving near the specific dealer building, not just visiting the city (see Sources below) |
| Stat milestones | Live telemetry (accumulated) | e.g. "Drive 500km total", "Complete 25 deliveries", "Earn 50,000 XP" -- running totals the bridge client keeps itself, not a single save field |

City discovery and dealer-unlock locations need a **new detection mechanism**: periodic
save-file reads (the game writes `autosave_drive_N` snapshots while actively driving, see
docs/design-decisions.md), diffed against the last-seen list -- not live telemetry, since
there's no shared-memory event for either. This is read-only, same safety profile as every
other check detection so far; only Sync (applying items) needs the main-menu precondition.

## Items

| Item | Effect | Mechanism |
|---|---|---|
| Money Bundle | +money | `bank.money_account` edit (proven, Milestone 4) |
| XP Grant | +experience | `economy.experience_points` edit -- same mechanism as money, different field. Replaces the originally-planned `g_exp_gain` config.cfg approach (global, relaunch-only, rate not flat) now that a direct flat grant is confirmed possible |
| Fine (Trap) | -money | Same mechanism as Money Bundle, negative delta |

Truck/part unlocks and garage ownership are **not** part of this item list. `game_progress.
owned_trucks` is very likely a historical/achievement log rather than a functional purchase
gate (vanilla ETS2 has no truck-unlock mechanic -- every truck brand is purchasable by
default), and `garage.<city>.status` has no confirmed-safe semantics or known side effects.
Both stay deferred to Milestone 7, where real custom content (not vanilla trucks) would need
its own gating mechanism anyway.

### Follow-up: suppressing natural XP gain (`g_exp_gain`)

To make XP Grant items matter rather than being a minor bonus on top of normal leveling, the
`g_exp_gain` config.cfg cvar (the multiplier on how fast the game itself grants XP from normal
play -- distinct from `experience_points`, which XP Grant items edit directly and which this
multiplier has no effect on) can be set near zero, making AP-granted XP the dominant way to
level up. Considered and rejected going further (gating specific cargo types like hazmat/
fragile/high-value behind skill-point thresholds as real access rules) for this pass: that
would need real research first (the exact skill-point save structure and per-job unlock
thresholds aren't confirmed, only that `experience_points` itself is a plain writable field),
whereas the simple version needs nothing beyond a config.cfg writer.

Built `bridge/sync/config_cfg.py` for this -- distinct from `sii_format.py` since config.cfg
is a flat, order-independent list of `uset <key> "<value>"` lines (confirmed CRLF throughout
on a real installation), not a nested unit structure. **Important caveat**: config.cfg is
installation-wide, not per-profile like a save file -- setting `g_exp_gain` here suppresses
XP gain on every profile on this install, not just one dedicated to an AP run, until it's
reset back. Confirmed working: `g_exp_gain` was unset on this installation (`get_cvar`
returned `None`); `set_cvar` appended `uset g_exp_gain "0.01"` and created a timestamped
backup, matching the same backup-before-write discipline as every other edit in this project.

### Follow-up: real city data for all 341 cities, DLC-gated

The original 4-city starter list (Kassel, Hannover, Frankfurt, Nurnberg) is now replaced with
the full real city catalog -- **341 cities** (80 base game + 261 across the 9 map DLCs) --
extracted directly from the game's own archives rather than guessed from community sources.

**How**: SCS's `.scs` archives are their own "HashFS v2" format (confirmed via magic bytes,
`SCS#`), not plain zip. Used `sk-zk/Extractor` (the tool referenced favorably in SCS's own
official forum, not just a random repo) to list `/def/city/*.sui` inside `def.scs` (base game)
and each DLC's own archive (e.g. `dlc_east.scs` for Going East!) -- each DLC has its own
separate city listing for its exclusive cities, no overlap found across any of the 10
archives. City ids matched every previously-confirmed one exactly (`kassel`, `hannover`,
`frankfurt`, `nurnberg`, and `bremen` -- the last found live during testing above). One
format quirk handled: a few filenames carry a `.dlc_xxx` disambiguator baked into the archive
path itself (e.g. `aalborg.dlc_north.sui`) -- confirmed this is a real archive-internal
naming detail, not an extraction artifact, and stripped it to get the canonical id. Display
names are auto-derived (title-cased id, underscores to spaces) -- fine for most, a few
(accented names, unusual capitalization) may read a little oddly and can be special-cased
later; checked for and found zero display-name collisions across all 341.

**Scope decision**: use the full list rather than hand-curating a smaller subset, gated by the
DLC toggle options that already existed in `options.py` but had no effect until now.
`apworld/ets2ats/city_data.py` holds `CITIES` (city_id -> (display_name, owning dlc key or
`None` for base)) and `DLC_OPTION_NAMES` (dlc key -> the matching option attribute name).
`Ets2AtsWorld._active_cities()` filters this by the player's actual DLC options and is used by
both `create_regions` (which locations exist) and `fill_slot_data` (what the client needs to
map a save's city ids to location names) so the two can never disagree -- the client no longer
imports a static city list at all, it gets `cities` from slot_data on connect instead, since
the active set now varies per seed.

**Confirmed working**: a base-game-only YAML generated exactly 176 locations
(80 cities x 2 + 10 deliveries + 3 distance + 3 XP); enabling all 9 DLCs on another YAML in
the same seed generated exactly 698 (341 x 2 + 16) -- confirming the DLC gating actually
changes the pool size correctly in both directions, not just that the option exists.

**`bridge/tools/detect_dlc.py`**: the local helper script anticipated in the original design
(`Generate.py` can't auto-detect a player's installed DLCs itself, since generation may run on
a different machine). Checks for each DLC's known `.scs` file's existence in the install
directory and writes the matching `dlc_*` values into a player's YAML. Confirmed working
against the real installation (correctly detected all 9 owned DLCs) via `pip install PyYAML`.
Deliberately does not import `city_data.py`'s `DLC_OPTION_NAMES` (would require a full
Archipelago checkout on `PYTHONPATH` just to run a file-existence check) -- its own `DLC_FILES`
key set must be kept in sync with `city_data.py` by hand.

## Goal (player-selectable, one per seed)

A `Choice` option lets the player pick which win condition applies to their world -- deliberately
supporting an achievable-in-a-day goal rather than defaulting to 100%-completion or a large
delivery count.

| Goal | Condition | Detection |
|---|---|---|
| Flawless Long-Haul Delivery | One delivery with distance >= `goal_distance_km` (default ~1200) and cargo damage <= `goal_max_damage_pct` (default ~1.0%) | Live telemetry (`jobDeliveredDistanceKm`, `jobDeliveredCargoDamage`) -- no new mechanism |
| Money Target | `bank.money_account` >= `goal_money` (default 1,000,000) | Save-file poll |
| Delivery Count | Cumulative deliveries >= `goal_delivery_count` (default 25) | Live telemetry (same counter Delivery #N locations already use) |
| XP Amount | `economy.experience_points` >= `goal_xp` (default TBD) | Save-file poll |

**Confirmed live**: `jobDeliveredDistanceKm` (the field behind both distance milestones and the
Flawless Long-Haul Delivery goal) is over-the-road distance only -- a delivery that included a
ferry crossing did not have the ferry leg counted toward it. SCS's own SDK docs just describe
it as "the real distance in km on the job" without settling this either way, and ferry use is
tracked as an entirely separate gameplay event from job delivery, so this was worth confirming
empirically rather than assuming. Relevant for `goal_distance_km` tuning: a route's ferry
segments don't help reach the threshold, only the driven portions do.

Implementation shape: a single always-reachable "Victory" location holding a "Victory" event
item, with `multiworld.completion_condition[player] = lambda state: state.has("Victory",
player)`. The bridge client watches whichever signal matches the chosen goal type (telemetry
or save-poll, per the table above) and calls `check_locations` on Victory once satisfied, then
reports `ClientStatus.CLIENT_GOAL` -- the same detect-and-report shape every other check
already uses, not a new pattern.

## Player options

- **Goal type** (Choice, see above) + one numeric threshold option per goal type.
- **Map DLC toggles**, one per major ETS2 map expansion, so the location pool only includes
  cities/dealers the player actually owns. `Generate.py` reads a static YAML and may run on a
  machine other than the player's own (a host generating for the group, or the website
  generator), so the **world itself cannot auto-detect installed DLC at generation time**.
  Instead, a small local helper script (same shape as `prototypes/sync_apworld.py`) will
  detect installed DLCs by checking for known files in the game's install directory and write
  the right option values into the player's YAML for them -- same practical outcome as
  auto-detection, just run as a pre-step rather than inside generation.
- **ETS2 / ATS / both**: still open, deferred until ATS-specific research (DLC filenames, city
  list, whether the same save-field names apply) happens -- not done as part of this pass.

### Confirmed DLC file mapping (this machine's ETS2 install)

| DLC | File |
|---|---|
| Going East! | `dlc_east.scs` |
| Scandinavia | `dlc_north.scs` |
| Vive la France! | `dlc_fr.scs` |
| Italia | `dlc_it.scs` |
| Beyond the Baltic Sea | `dlc_balt.scs` |
| Road to the Black Sea / West Balkans | `dlc_balkan_e.scs` / `dlc_balkan_w.scs` (east/west split inferred geographically, not yet confirmed against SCS's own docs) |
| Iberia | `dlc_iberia.scs` |
| Greece | `dlc_greece.scs` |

## Save-file findings this design is grounded in

All confirmed against a real, played save (`profiles/4D6F642054657374/save/autosave/game.sii`,
the Mod Test profile), not assumed from documentation:

- `economy.visited_cities` / `economy.visited_cities_count` -- flat string array, e.g.
  `["kassel", "hannover", "frankfurt", "nurnberg"]`.
- `economy.unlocked_dealers` -- flat string array, confirmed **not** identical to
  `visited_cities` (a city can be visited without its dealer being unlocked -- Nürnberg was
  visited but not in `unlocked_dealers` in the same save). Confirmed writable and effective
  via a live spike test: appending `"nurnberg"` and loading the profile made a truck dealer
  actually appear there in-game.
- `economy.experience_points` -- plain integer scalar (found at `580`), same shape as
  `bank.money_account`.
- `game_progress.owned_trucks` -- flat string array of truck model IDs (e.g.
  `["vehicle.iveco.sway"]`) -- likely just a historical log, not a purchase gate (see above).
- `garage.<city_id>.status` -- one `garage` unit per city (234 in this save), `status: 0` on
  every unowned one observed. No second data point to infer what a non-zero value means or
  what else a real purchase updates alongside it -- not used in this design.

### Spike test note: a bug in the test script, not the save format

The first attempt at the `unlocked_dealers` spike test crashed looking up a `player`-type
unit referenced by `economy.player` -- a mistake, not a data-loss bug. `visited_cities`,
`unlocked_dealers`, and `experience_points` live directly on the `economy` unit itself; the
unit `economy.player` *references* is a different, confusingly similarly-named `player`-type
unit holding vehicle/HQ/driving-time state (`hq_city`, `my_vehicles`, `driving_time`, etc.).
Worth remembering when writing the real save-poller: know which unit actually owns a field
before reading/writing it, since two units can plausibly share a name-adjacent role.

Sources: [Unlocking truck dealerships :: Euro Truck Simulator 2 General Discussions](https://steamcommunity.com/app/227300/discussions/0/2566438792572116584/?l=english), [ETS2 Truck Dealers Guide: Unlock, Visit, and Buy Safely | ETS2Hub](https://www.ets2hub.com/guides/ets2-truck-dealers-guide)

## Implementation notes

The apworld split into `options.py`/`items.py`/`locations.py`/`rules.py` per the tutorial
shape (Milestones 3-5 kept everything in one file since there was no real design yet to
justify splitting it). `location_name_to_id`/`item_name_to_id` are the full static universe
across every option combination (e.g. `Delivery #1`..`Delivery #100`, even though a given
seed only ever activates `delivery_location_count` of them) -- Archipelago requires this
table to be stable regardless of a specific seed's options.

**One real bug caught**: the first attempt at the Victory location crashed `Main.py`'s
`write_multidata` with `AssertionError: item code None should be event, location.address
should then also be None`. An event item (`code=None`, used so the "Victory" item is never
actually sent over the network) must be placed on a location that is *also* a pure event
location (`address=None`), not a normal numbered one -- confirmed against how the `adventure`
world's own "Chalice Home" final location is defined (`LocationData(..., None, event=True)`).
Fixed by constructing the Victory location with `address=None` directly rather than pulling a
real ID from `LOCATION_NAME_TO_ID`.

The save-poller (`bridge/sync/save_poller.py`'s `read_tracked_fields`, polled every 20s by
`client.py`'s `save_poller` task) and the telemetry watcher are intentionally asymmetric in
one way: the save-poller never prompts for confirmation on a profile-name mismatch (unlike
Sync/`apply_deltas`), because it's read-only -- misattributing a discovery to the wrong
profile is a minor logical mismatch, not a corruption risk, so it just logs a warning once and
falls back silently. Confirmation is reserved for the one operation that actually writes.

On first connect, the save-poller treats every already-satisfied condition in the save
(cities already visited, dealers already unlocked before this AP session even started) as
newly discovered and checks it immediately -- confirmed in testing (see above). This is
intentional, not a bug to guard against: it matches the standing assumption that the ETS2
profile is dedicated to this AP run (the very first architecture idea raised for this whole
project), so any progress already on that profile legitimately counts.

DLC toggles now drive real location generation and the detection helper script exists (see the
"real city data" follow-up above, done in a later pass). ATS support, and confirming the
`dlc_balkan_e`/`dlc_balkan_w` naming against SCS's own docs, remain open.

### A second real bug, caught before it could bite: double-applying items on reconnect

The original design tracked pending items as a plain list the client appended to on every
`ReceivedItems` packet, persisted to `pending_items.json`. This is wrong: Archipelago resends
a player's **full item history** on every reconnect (`CommonClient.py`'s `ReceivedItems`
handler rebuilds `ctx.items_received` from `index=0` whenever a client reconnects), not just
items received since the client was last open. A client that already applied those items to
the save in a previous session would see them arrive again, re-queue them, and double-apply
them on the next Sync -- silently duplicating money/XP with no error to signal it.

Caught before running a second live test against a multiworld with existing check history
(exactly the scenario that would have triggered it). Fixed by tracking a single integer,
`items_applied_count`, instead of a separately-maintained item list: `ctx.items_received` is
CommonContext's own authoritative, reconnect-safe list (confirmed by reading
`process_server_cmd` -- it fully rebuilds `items_received` before calling `on_package`, so
relying on it there is safe), and "pending" is simply
`ctx.items_received[ctx.items_applied_count:]`. Sync advances the counter to
`len(ctx.items_received)` on success rather than clearing a list. Persisted to
`sync_state.json` (renamed from `pending_items.json` to reflect what it actually stores).

### A third real bug, caught live: check-detection state only ever lived in memory

`delivery_count`, `cumulative_distance_km`, and the milestone/city/dealer "already sent"
tracking sets were plain instance attributes with no persistence at all. Three client restarts
during live telemetry-bug fixing (see docs/design-decisions.md) reset `delivery_count` to 0
each time -- so a real post-restart delivery got labeled "Delivery #1" again, collided with
the already-checked location of that exact name, and the check was silently a no-op. At least
one genuine delivery during that window produced no check and no item at all, with nothing in
the logs to distinguish it from a legitimate duplicate.

`visited_cities_seen`, `unlocked_dealers_seen`, and `xp_milestones_sent` turned out not to
need this fix for correctness (though they got it anyway, for consistency) -- they're
reconstructed fresh from the save file's own ground truth on the very first save-poll after any
restart, since `read_tracked_fields` always reads the *current* full state, not a delta. Only
`delivery_count` and `cumulative_distance_km` are pure running tallies with no equivalent
ground-truth field to re-derive from, which is exactly why only those two caused a real,
unrecoverable gap. Fixed by persisting all six together (`client_state.json`, renamed again
from `sync_state.json` now that it covers more than sync), written after every state change in
both `telemetry_watcher` and `save_poller`.

Migrating the existing test session's state needed judgment, not just a mechanical copy:
`items_applied_count` (8) was carried over exactly, since getting it wrong risks double-
applying real money/XP. `delivery_count` and `cumulative_distance_km` couldn't be reconstructed
exactly (deliveries lost during the broken window weren't logged in enough detail to count),
so they were seeded conservatively from only the two precisely-logged real deliveries
(215.0km + 394.0km = 609.0km; `delivery_count: 1`, matching the one delivery that actually
produced a check) -- safe because undercounting a running tally only delays the next threshold
slightly, while overcounting it would have permanently skipped ones never actually granted.
