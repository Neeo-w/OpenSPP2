# Alkathiry Base — Registration, Lineage & Positions

One consolidated thin layer over OpenSPP. The tribal lineage is carried on the
existing registry **Groups** (no separate model), so it shows up natively in
*Browse All Groups* and reuses the group type / membership / registry features.

## Lineage on registry groups (res.partner)
A tribe node **is** a registry group (`is_group=True`). On the group we add the
same dynamic hierarchy `spp.area` uses for geography:
- **`alk_lineage_parent_id`** — the single "Parent Tribe" (grand tribe > tribe >
  batn > clan > fakheedah > family).
- **`alk_lineage_complete_name`** / **`alk_lineage_level`** / **`alk_lineage_path`**
  — recursive stored computes (our manual equivalent of `spp.area.parent_path`,
  since `res.partner` already owns the native `parent_id` tree).
- The **level** is the standard `group_type_id` (vocabulary
  `urn:openspp:vocab:group-type`), seeded with the tribal levels and flagged
  `allow_all_member_type` so a node can contain sub-groups (group-of-groups).

## Models
- **`alkathiry.tribe.position`** — the positions matrix:
  `tribe_id (group) × area_id → position_id + responsible user_id`. The same
  node can have a different official per country.
- **`alkathiry.health.condition`** — diseases with proof attachments (complements
  the functional disability registry).

## res.partner additions (individuals)
`alk_citizen_no` (generated), `alk_tribe_node_id` (→ the registry group the
citizen belongs to), `alk_representative_ids` (computed: officials resolved from
the matrix by intersecting the citizen's lineage node + ancestors with their
area), blood type, general health status, education level, employment status,
financial status, medical conditions. Reused as-is: `civil_status_id`,
`occupation_id`, `income`, `address`, `area_id`.

## UI
- Group form (Browse All Groups): **Tribal Lineage** block (Parent Tribe / level)
  on the Profile tab + a **Tribal Structure** tab (sub-tribes + positions).
- Registry app → **Tribes & Positions** → *Tribal Lineage* (groups grouped by
  Parent Tribe) + *Positions*.
- Individual fields are appended into the existing **Profile** tab (no new tab).

## Terminology
All option lists are `spp.vocabulary.code` (admin-editable): group-type (lineage
levels), position, blood-type, health-status, education-level, employment-status,
financial-status, disease.

## Dependencies
`spp_registry`, `spp_registry_group_hierarchy`, `spp_area`, `spp_vocabulary`,
`spp_disability_registry`. Odoo 19.0.
