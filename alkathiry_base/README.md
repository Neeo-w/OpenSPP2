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

## Bodies & leadership ladders (one infrastructure, many structures)
The same group + lineage + positions infrastructure models any hierarchical body
of registrants — tribal nodes, **unions/syndicates** and **organizations** —
each scoped per country and built from vocabulary:
- A union/organization **is** a registry group too, typed via `group_type_id`
  (`union` / `organization` / `activity` added to the shared group-type vocab).
- **`alkathiry.tribe.position`** is the universal leadership matrix:
  `body (group) × track × area_id → position_id + official (+ Reports To)`.
  - **`track_id`** (`urn:alkathiry:vocab:position-track`: sheikhs / aqils / union /
    organization) separates the parallel ladders; a chain never crosses tracks.
  - `parent_position_id` chains the ladder; constraints enforce same track and
    that the parent's area covers the child's — so each ladder is independent
    per country (Al-Kathir sheikhs in Yemen vs in Saudi Arabia).
- **`alkathiry.health.condition`** — diseases with proof attachments (complements
  the functional disability registry).

A citizen sits at the intersection: **country (area) → tribe (lineage) →
officials (sheikhs/aqils) → affiliations (unions/organizations)**. Affiliations
use standard `spp.group.membership` (extended with related `group_type_id` /
`group_area_id`), so one unified list on the profile covers every body type with
no per-type field.

## res.partner additions (individuals)
`alk_citizen_no` (generated), `alk_tribe_node_id` (→ the registry group the
citizen belongs to), `alk_representative_ids` (computed: officials resolved from
the matrix by intersecting the citizen's lineage node + ancestors with their
area), blood type, general health status, education level, employment status,
financial status, medical conditions. Reused as-is: `civil_status_id`,
`occupation_id`, `income`, `address`, `area_id`.

## UI
- Group form (Browse All Groups): **Tribal Lineage** block on the Profile tab +
  a **Structure & Positions** tab (sub-structures + leadership positions with
  track). Shared by tribes, unions and organizations.
- Registry app → **Community Structures** → *Tribal Lineage*, *Unions &
  Syndicates*, *Organizations*, *Positions / Ladders* (grouped by track & area).
- Citizen Profile tab: community profile + health + a unified **Affiliations**
  list (tribe / unions / organizations / activities) grouped by body type.

## Terminology
All option lists are `spp.vocabulary.code` (admin-editable): group-type (lineage
levels + union / organization / activity), position-track, position, blood-type,
health-status, education-level, employment-status, financial-status, disease.

## Dependencies
`spp_registry`, `spp_registry_group_hierarchy`, `spp_area`, `spp_vocabulary`,
`spp_disability_registry`. Odoo 19.0.
