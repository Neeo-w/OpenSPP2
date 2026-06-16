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

## Tribal leadership ladders (sheikhs / aqils)
- **`alkathiry.tribe.position`** is the tribal leadership matrix:
  `tribe node (group) × track × area_id → position_id + official (+ Reports To)`.
  - **`track_id`** (`urn:alkathiry:vocab:position-track`: sheikhs / aqils)
    separates the parallel ladders; a chain never crosses tracks.
  - `parent_position_id` chains the ladder; constraints enforce same track and
    that the parent's area covers the child's — so each ladder is independent
    per country (Al-Kathir sheikhs in Yemen vs in Saudi Arabia).

## Unions & organizations (dedicated bodies — NOT registry groups)
Unions/syndicates and organizations are their own entity, with their own clean
screens. They belong to their **members (individuals)**, never to a tribe.
- **`alkathiry.organization`** — name, `org_type_id` (union / federation /
  organization / association / cooperative), `category_id` (engineers / farmers /
  doctors / health / agriculture…), `area_id` (country), address / phone / email,
  `date_established`, `code` (registration no.), `president_id` (an individual),
  optional `parent_id` for national→regional branches, and `member_ids`.
- **`alkathiry.organization.member`** — links an **individual** to a body with a
  `role_id` (president / vice / secretary / treasurer / board / member),
  membership no. and dates.
- **`alkathiry.health.condition`** — diseases with proof attachments.

A citizen sits at the intersection: **country (area) → tribe (lineage) →
tribal officials (sheikhs/aqils, resolved) → union/organization memberships**.
The memberships appear on the citizen's Profile as a dedicated list.

## res.partner additions (individuals)
`alk_citizen_no` (generated), `alk_tribe_node_id` (→ the registry group the
citizen belongs to), `alk_representative_ids` (computed: officials resolved from
the matrix by intersecting the citizen's lineage node + ancestors with their
area), blood type, general health status, education level, employment status,
financial status, medical conditions. Reused as-is: `civil_status_id`,
`occupation_id`, `income`, `address`, `area_id`.

## UI
- Registry app → **Community Structures** → *Tribal Lineage* (groups) + *Tribal
  Positions (Sheikhs / Aqils)*.
- Registry app → **Unions & Organizations** → *Unions & Syndicates* +
  *Organizations* — each a dedicated screen on `alkathiry.organization`
  (own form: classification, location/contact, president, members tab).
- Citizen Profile tab: community profile + health + a dedicated **Union /
  Organization Memberships** list (linked to the person, with role).

## Terminology
All option lists are `spp.vocabulary.code` (admin-editable): group-type (lineage
levels), position-track (sheikhs / aqils), position, org-type, org-category,
org-role, blood-type, health-status, education-level, employment-status,
financial-status, disease.

## Dependencies
`spp_registry`, `spp_registry_group_hierarchy`, `spp_area`, `spp_vocabulary`,
`spp_disability_registry`. Odoo 19.0.
