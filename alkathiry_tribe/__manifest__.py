# pylint: disable=pointless-statement
{
    "name": "Alkathiry Tribe — Lineage Tree & Positions",
    "summary": "A clean parent/child/level lineage tree (alkathiry.tribe) for the "
    "tribal nasab — independent of geography — plus a structural positions matrix "
    "(alkathiry.tribe.position) linking tribe x area x position x responsible "
    "official. Solves transnational representation: the same clan can have a "
    "different leader per country.",
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
        "alkathiry_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/tribe_type_vocabulary.xml",
        "views/tribe_views.xml",
        "views/tribe_position_views.xml",
        "views/individual_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
