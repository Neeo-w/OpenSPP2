# Alkathiry Base — Registration & Hierarchy Layer

Thin layer over OpenSPP. **Inherits** the existing registry/hierarchy/area/
vocabulary modules and **adds only** what is missing for the Alkathiry community
profile. No model is duplicated.

## What it adds
- **Profile fields** on the individual registrant (`res.partner`): tribe pointer,
  marital status, blood type, education level, employment status, health status,
  financial status, occupation, monthly income, detailed address, additional info,
  and a generated `Citizen No.` (concept borrowed from OpenG2P `unique_id`).
- **Dynamic terminology (vocabularies)** seeded as `is_system=False` so the
  Central Committee edits the option lists from the UI: marital-status, blood-type,
  education-level, employment-status, health-status, financial-status, position.
- **Tribal hierarchy levels** as codes on the existing `urn:openspp:vocab:group-type`
  vocabulary with `allow_all_member_type=True` (neighborhood / grand_tribe / tribe /
  clan) — enabling the group-of-groups tribal tree.
- **Individual form page** "Alkathiry Profile" exposing the new fields.

## How the hierarchies link (unchanged OpenSPP mechanics)
- **Region**: `res.partner.area_id` → `spp.area` (tree), added by `spp_area`.
- **Tribe/Family**: `spp.group.membership` chains over `res.partner` groups whose
  `group_type_id` is a tribe-level code (this module seeds those codes).
- **Convenience pointer**: `alk_tribe_id` denormalizes the tribal node for quick
  filtering; the authoritative link stays the membership records.

## Dependencies
`spp_registry`, `spp_registry_group_hierarchy`, `spp_area`, `spp_vocabulary`.
Targets Odoo 19.0.

## Not included (later phases)
Scoped roles by position (`local_tribe_ids`), the approval position-router,
service distribution — see `alkathiry_docs/` planning documents.
