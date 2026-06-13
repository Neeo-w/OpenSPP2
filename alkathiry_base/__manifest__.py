# pylint: disable=pointless-statement
{
    "name": "Alkathiry Base — Registration & Hierarchy Layer",
    "summary": "Thin layer over OpenSPP that adds ONLY the missing Alkathiry "
    "community profile dimensions (tribe pointer, citizen number, blood type, "
    "health/employment/financial status, education level), seeds the dynamic "
    "terminology (vocabularies) and the tribal hierarchy levels. Reuses existing "
    "spp_registry fields (civil_status_id, occupation_id, income, address) and "
    "spp_area (area_id) without duplicating them.",
    "category": "Alkathiry/Registry",
    "version": "19.0.1.0.0",
    "author": "Alkathiry Project",
    "website": "https://github.com/Neeo-w/openspp2",
    "license": "LGPL-3",
    "development_status": "Alpha",
    "depends": [
        "spp_registry",
        "spp_registry_group_hierarchy",
        "spp_area",
        "spp_vocabulary",
    ],
    "data": [
        "data/ir_sequence.xml",
        "data/alkathiry_vocabularies.xml",
        "data/group_type_tribe_levels.xml",
        "views/individual_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
