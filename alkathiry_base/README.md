# Alkathiry Base — Registration & Hierarchy Layer

Thin layer over OpenSPP. **Inherits** the existing registry/hierarchy/area/
vocabulary modules and **adds only what has no existing equivalent**. Audited
against the codebase to avoid duplicating fields (same name) or concepts
(same scenario, different name).

## Reused as-is (NOT re-added)
| Concept | Existing field/module |
|---|---|
| Marital status | `civil_status_id` (spp_registry, UN marital-status vocab) |
| Occupation | `occupation_id` (spp_registry, ISCO-08 vocab) |
| Income | `income` (spp_registry) |
| Address | `address` (spp_registry) |
| Region link | `area_id` (spp_area) |
| Disability | `spp_disability_registry` (assessments, severity) |
| Notes | base `res.partner.comment` |

## What it adds (genuinely new)
- **Fields on the individual** (`res.partner`): `alk_citizen_no` (generated),
  `alk_tribe_id` (tribal pointer), `alk_blood_type_id`, `alk_health_status_id`
  (general, not disability), `alk_education_level_id`, `alk_employment_status_id`
  (distinct from occupation), `alk_financial_status_id` (bracket, distinct from
  numeric income).
- **Vocabularies** (`is_system=False`, admin-editable): blood-type, health-status,
  education-level, employment-status, financial-status, position.
- **Tribal hierarchy levels** as codes on the existing `urn:openspp:vocab:group-type`
  vocabulary with `allow_all_member_type=True` (neighborhood / grand_tribe / tribe /
  clan).
- **"Alkathiry Profile" page** on the individual form, ordered into Community
  Identity · Demographics & Health · Education & Employment · Economic Status.

## How the hierarchies link (native OpenSPP mechanics)
- **Region**: `res.partner.area_id` → `spp.area` tree (from `spp_area`).
- **Tribe/Family**: `spp.group.membership` chains over groups whose `group_type_id`
  is a tribe-level code (seeded here); `alk_tribe_id` is a convenience pointer.

## Dependencies
`spp_registry`, `spp_registry_group_hierarchy`, `spp_area`, `spp_vocabulary`. Odoo 19.0.
