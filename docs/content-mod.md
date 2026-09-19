# Milestone 7: companion content mod

Scoped after Milestone 6. Distinct from `docs/game-design.md` (locations/items/rules) and
`docs/design-decisions.md` (bridge/telemetry technical findings) -- this covers the actual
`.scs` mod (`content-mod/`) and what building it revealed about SCS's modding format.

## Scope decision: always-purchasable cosmetics, not hard AP-exclusive gating

The original vision (see early design discussion) imagined mod-added content that stays
*locked* until an AP item unlocks it -- a real gate, not just a cosmetic bonus. Investigated
and set aside for this pass, in favor of new paint jobs that are always purchasable, with AP's
role being to grant the money to buy them (reusing the money-item mechanism already proven in
Milestone 4/6, no new save-editing mechanism needed). Two concrete blockers to hard gating,
found while researching real game data rather than assumed:

- **Paint job ownership isn't a simple flat list.** Unlike `unlocked_dealers`/`visited_cities`
  (flat string arrays we already edit safely), which specific paint job a truck has is part of
  that truck's own `vehicle` unit (`accessories[]` pointing to a `vehicle_paint_job_accessory`
  unit) -- a per-vehicle-instance data structure we haven't attempted editing, meaningfully more
  complex than anything touched so far.
- **The one clear precedent for "complete something, unlock a cosmetic"** is the free Academy
  DLC's `academy_reward` field (seen on a real extracted paint job def, e.g.
  `academy_reward: "academy_book_1"`) -- but the real save file used throughout this whole
  project never engaged with that DLC content, so there's no ground truth to read the actual
  tracking field's name/shape from. Guessing at it would break the project's own established
  practice of confirming mechanisms against real data before relying on them.

Both are legitimate future research directions (worth another look once there's a save file
that has actually progressed through Academy content, or an experimental attempt at
constructing a `vehicle_paint_job_accessory` unit), but out of scope for a first content mod.

## How a paint job is actually defined (real data, not documentation)

Extracted directly from the game's own `def.scs` via `sk-zk/Extractor` (the same tool used for
the Milestone 6 city data), rather than inferred from tutorials -- e.g. `/def/vehicle/truck/
man.tgx/paint_job/style1.sii`:

```
accessory_paint_job_data : style1.man.tgx.paint_job
{
    name: "@@pj_bubbles@@"
    price: 12500
    unlock: 5
    icon: "paintjob_style1"
    part_type: aftermarket
    mask_r_color: (0.9559, 0.6653, 0.1412)
    mask_r_locked: true
    ...
    paint_job_mask: "/vehicle/truck/upgrade/paintjob/paintjob_001.tobj"
    alternate_uvset: true
    color_variant[]: (...)
}
```

Two findings that shaped the mod:

- **`paint_job_mask` is often a generic, shared texture reused across many differently-named
  paint jobs** (`paintjob_001.tobj` here isn't specific to this truck or this style) -- meaning
  a new paint job can reference this exact existing asset with new name/price/colors, needing
  **zero new texture/art assets**. Confirmed by comparing two real paint jobs for the same
  truck that reference the same mask file with different colors.
- **`unlock` is very likely a plain driver-level requirement** (a bare integer, `5` here vs `0`
  on the Academy example), not a complex flag system -- `academy_reward` looks like a separate,
  additional field layered on top for that one DLC-specific case. Setting `unlock: 0` matches
  our "always purchasable" scope directly.

## Mod packaging format

Confirmed via SCS's own official forum guide and modding wiki: a **user mod `.scs` file is
just a plain, uncompressed zip archive renamed to `.scs`** -- a completely different, much
simpler format from the HashFS v2 archives the game's own shipped content uses (which required
a third-party extractor to even read). `content-mod/build.py` packages the mod folder this way
(`zipfile.ZIP_STORED`, matching the documented "noncompressed" convention) -- no HashFS writer
needed at all for our own content.

## First content: `content-mod/def/vehicle/truck/man.tgx/paint_job/ap_bundle_1.sii`

One new paint job, "Archipelago Special", for the MAN TGX: `price: 50000`, `unlock: 0`,
reusing the confirmed-shared `paintjob_001.tobj` mask with a distinct purple/gold color scheme.
Built and packaged (`content-mod/build.py` -> `content-mod/dist/archipelago_rewards.scs`),
installed into the game's `mod/` folder for a live test.

**Working assumption, not yet confirmed**: paint job files are auto-discovered by the game
from their folder location (no central per-truck registration file listing them) -- inferred
from every other upgrade category (cabin, chassis, engine, transmission, interior) also being
loose, unindexed per-file definitions with nothing else in the truck's own directory
referencing them by name, consistent with how community "paint job pack" mods are documented
to work. To be confirmed by the live in-game test.

### "MAN TGX" is actually three separate vehicles

Asked before testing which specific truck to check, which surfaced something worth recording:
`/def/vehicle/truck/` has **three distinct MAN TGX folders** -- `man.tgx` (the classic model,
what the first version of this content targeted), `man.tgx_euro6` (the classic model's Euro6
emissions variant, also base game, a fully separate folder with its own cabins/chassis/paint
jobs), and `man.tgx_2020` (the all-new refreshed model, gated behind its own paid DLC). A mod
entry for one does not cover the others.

Added the same paint job under `man.tgx_euro6` too (still out of scope: the DLC-gated 2020
model). One real structural difference found while doing this: **`man.tgx_euro6` has no
generic reusable mask** the way classic `man.tgx` does -- every aftermarket paint job examined
(`com_0`, `manba10`, `manba11`, ...) references its own unique per-style texture path, and a
plain `stock: true` factory color (e.g. `ral_5010.sii`) needs no mask at all. Reused an
existing per-style mask (`man_tgx_euro6/com_0/...`) for our own definition rather than
requiring new art, and mirrored a real entry's `suitable_for[]` cabin/chassis compatibility
list rather than omitting it (unlike the classic model, every Euro6 example included one).
