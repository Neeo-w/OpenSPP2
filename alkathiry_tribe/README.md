# Alkathiry Tribe — Lineage Tree & Positions

Answers three needs that the generic group-membership model did not express well:

## 1. A clear parent/child/level lineage tree
`alkathiry.tribe` is a proper `_parent_store` hierarchy (like `spp.area` is for
geography): `parent_id`, `child_ids`, `parent_path`, computed `level`, and a
`tribe_type_id` (grand tribe / tribe / clan / fakheedah / family — admin
vocabulary). You link a tribe to another tribe with the **Parent** field, and
`child_of` / `parent_of` queries work natively. It is **independent of geography**.

## 2. A structural tribal-positions module
`alkathiry.tribe.position` = the representation matrix:
`tribe_id × area_id → position_id + user_id (+ parent_position_id)`.
The same lineage node can have a different official per country (a Sheikh in
Salalah, a Muqaddam in Seiyun). Officials, tribes and regions are all linked here.

## 3. Correct representation (not "Group Membership")
The individual points to a **Lineage Node** (`alk_tribe_node_id`), and
`alk_representative_ids` resolves the responsible officials by intersecting that
node with the citizen's `area_id` against the matrix. Group membership stays for
households/families (where "members" is the right concept); lineage uses this tree.

## Regions
Region hierarchy is already a clean tree in `spp.area` (`parent_id` / `area_type`)
— no change needed; the positions matrix references it via `area_id`.

## Dependencies
`spp_registry`, `spp_area`, `spp_vocabulary`, `alkathiry_base`. Odoo 19.0.
