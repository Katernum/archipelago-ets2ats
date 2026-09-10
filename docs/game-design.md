# Milestone 6 game design

The real location/item/rules design, scoped after Milestone 5. Distinct from
`docs/design-decisions.md` (technical findings/pitfalls) -- this is the actual game spec,
grounded in real fields found in a live save file (see "Save-file findings" below) rather
than assumption. Nothing here is implemented yet; this is the target for Milestone 6's build.

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

## Not yet built (this document is design only)

- Save-file poller (city discovery, dealer unlocks, money/XP goal detection) -- a new
  component alongside the existing live telemetry watcher.
- DLC-detection helper script.
- `apworld/ets2ats/options.py` (goal type + per-goal thresholds + DLC toggles) -- the apworld
  is currently one flat `__init__.py`; this is likely the point where it needs to split into
  modules (options.py/locations.py/items.py/rules.py), matching the official APQuest tutorial
  shape referenced back in Milestone 3.
- Victory location + `completion_condition` wiring.
- Stat-milestone tracking (distance/XP/delivery-count running totals) in the bridge client.
