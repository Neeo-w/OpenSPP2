# Alkathiry Base — Registration, Lineage & Positions

One consolidated thin layer over OpenSPP. Inherits the registry/area/vocabulary/
disability modules and adds only what is missing, all vocabulary-driven.

## Models
- **`alkathiry.tribe`** — the lineage (nasab) tree: a clean `_parent_store`
  parent/child/level hierarchy (like `spp.area` is for geography), independent of
  any country. `tribe_type_id` is a vocabulary (grand tribe / tribe / batn / clan /
  fakheedah / family). Tribe-to-tribe linking via the **Parent** field.
- **`alkathiry.tribe.position`** — the positions matrix:
  `tribe_id × area_id → position_id + responsible user_id (+ parent_position_id)`.
  The same node can have a different official per country.
- **`alkathiry.health.condition`** — diseases with proof attachments (complements
  the functional disability registry).

## res.partner additions
`alk_citizen_no` (generated), `alk_tribe_node_id` (→ alkathiry.tribe),
`alk_representative_ids` (computed: officials resolved from the matrix by
intersecting the lineage node with the citizen's area), blood type, general health
status, education level, employment status, financial status, medical conditions.
Reused as-is: `civil_status_id`, `occupation_id`, `income`, `address`, `area_id`.

## UI
Registry app → **Tribes & Positions** → *Lineage Tree* + *Positions*. The new
individual fields are appended into the existing **Profile** tab (no new tab).

## Terminology
All option lists are `spp.vocabulary.code` (admin-editable): tribe-type, position,
blood-type, health-status, education-level, employment-status, financial-status,
disease.

## Dependencies
`spp_registry`, `spp_area`, `spp_vocabulary`, `spp_disability_registry`. Odoo 19.0.
