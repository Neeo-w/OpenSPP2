# pylint: disable=pointless-statement
{
    "name": "Alkathiry Base — Registration & Hierarchy Layer",
    "summary": "Thin layer over OpenSPP that adds the Alkathiry community profile "
    "(citizen number, blood type, health/employment/financial status, education "
    "level, medical conditions with proof), the clean lineage tree (alkathiry.tribe) "
    "with the tribal-positions matrix, and seeds the dynamic terminology "
    "(vocabularies). Reuses existing spp_registry fields (civil_status_id, "
    "occupation_id, income, address) and spp_area (area_id) without duplicating them.",
    "category": "Alkathiry/Registry",
    "version": "19.0.1.0.0",
    "author": "Alkathiry Project",
    "website": "https://github.com/Neeo-w/openspp2",
    "license": "LGPL-3",
    "development_status": "Alpha",
    "depends": [
        "spp_registry",
        "spp_area",
        "spp_vocabulary",
        "spp_disability_registry",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/alkathiry_vocabularies.xml",
        "data/tribe_type_vocabulary.xml",
        "views/health_condition_views.xml",
        "views/tribe_views.xml",
        "views/tribe_position_views.xml",
        "views/individual_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "pre_init_hook": "pre_init_hook",
}
