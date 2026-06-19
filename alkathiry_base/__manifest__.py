# pylint: disable=pointless-statement
{
    "name": "Alkathiry Base — Registration & Hierarchy Layer",
    "summary": "Thin layer over OpenSPP that adds the Alkathiry community profile "
    "(citizen number, blood type, health/employment/financial status, education "
    "level, medical conditions with proof), the tribal lineage carried on registry "
    "groups (res.partner) with the tribal-positions matrix, and seeds the dynamic "
    "terminology (vocabularies). Reuses existing spp_registry groups/fields "
    "(group_type_id, civil_status_id, occupation_id, income, address) and spp_area "
    "(area_id) without duplicating them.",
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
        "spp_disability_registry",
        "web_hierarchy",
        "mail",
    ],
    "data": [
        "security/doc_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/alkathiry_vocabularies.xml",
        "data/group_type_levels.xml",
        "data/structures_vocabulary.xml",
        "data/organization_vocabulary.xml",
        "data/tribal_relationship_codes.xml",
        "data/doc_vocabularies.xml",
        "data/doc_global_levels.xml",
        "views/health_condition_views.xml",
        "views/group_lineage_views.xml",
        "views/organization_views.xml",
        "views/individual_views.xml",
        "views/doc_views.xml",
        "views/doc_menus.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "pre_init_hook": "pre_init_hook",
}
