# pylint: disable=pointless-statement
{
    "name": "Alkathiry Base — Registration & Hierarchy Layer",
    "summary": "Thin layer over OpenSPP that adds the Alkathiry community profile "
    "fields (tribe, blood type, marital/health/employment/financial status, income, "
    "education level, address, additional details), wires the tribal/geographic "
    "hierarchies, and seeds the dynamic terminology (vocabularies). Inherits the "
    "existing registry, group-hierarchy, area and vocabulary modules; adds nothing "
    "that duplicates them.",
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
