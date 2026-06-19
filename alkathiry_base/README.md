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

## Dynamic certification engine — ONE hierarchy engine (merged from the ladder)
The old one-person-per-node ladder is **merged** into the spec's dynamic
multi-hierarchy certification model. ONE generic engine now serves every
structure (tribal / aqils / union / committee / administrative); only the
terminology changes.
- **`doc.hierarchy`** — a country-bound hierarchy the Secretary General builds via
  the UI (no code). `type_id` reuses the `position-track` vocabulary.
- **`doc.level`** — the generic stage (single engine). `kind` (position /
  department / committee / region / custom) is just a label; whatever the kind,
  the hierarchical option is always present: `sequence`, `parent_level_id`, and
  `documenter_ids` the beneficiary picks one of. Optional classifications reuse
  existing models — place = **`spp.area`**, committee = **`alkathiry.organization`**,
  job/department = lightweight vocabularies (no `hr` dependency).
  `_parent_store` + the **org-chart hierarchy view** render it top-down; a
  hierarchy can be **cloned to another country** (`doc.hierarchy.clone`).
- **`doc.documenter`** — a member assigned to a level with a `role_id`
  (manager / member / assistant / employee), optionally a system `user_id`.
- **Shared global top** — `is_global` levels (Secretary General + his committees)
  with no hierarchy, auto-appended to every route, so all routes end at the same
  place.

### Request workflow (bottom-up, mandatory sequence, audited)
- **`doc.request`** (`mail.thread`) — the beneficiary picks a hierarchy, the
  **route builder** (`doc.route.builder`) walks `parent_level_id` from the entry
  level up, auto-selecting single members and leaving multi-member levels for the
  beneficiary to choose; documents are uploaded and the request submitted.
- It is then assigned strictly to the **next member in the route** — no stage may
  be skipped — until the Secretary General, where it becomes `certified`. Each
  step is journalled in **`doc.request.log`** (audit trail) and the next member is
  notified (activity). `doc.request.route` holds the chosen member per level.
- **Security**: `group_doc_secretary` / `committee` / `documenter` / `beneficiary`
  with record rules — beneficiaries see their own requests, documenters only what
  is currently assigned to them, secretary/committee see all.

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
`spp_disability_registry`, `web_hierarchy` (org-chart view), `mail` (request
audit/notifications). Odoo 19.0.
