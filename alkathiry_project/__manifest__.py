# pylint: disable=pointless-statement
{
    "name": "Alkathiry Project — Dynamic Community Platform Core",
    "summary": "Fully dynamic, metadata-driven core data layer for the Alkathiry tribal "
    "digital community platform. Consolidates identity (MOSIP-inspired hierarchical "
    "verification), service quota & target allocation (OpenSPP-inspired), a double-entry "
    "financial ledger (Mifos X-inspired), dynamic credentials (Sunbird RC-inspired) and "
    "ad management into local, configurable Odoo models with zero hardcoded workflows.",
    "category": "Alkathiry/Core",
    "version": "19.0.1.0.0",
    "sequence": 1,
    "author": "Alkathiry Project",
    "website": "https://github.com/Neeo-w/openspp2",
    "license": "LGPL-3",
    "development_status": "Alpha",
    "depends": [
        "base",
        "mail",
    ],
    "external_dependencies": {
        "python": ["jwt"],
    },
    # Step 1: data layer. Step 2: hierarchical verification engine + admin UI.
    # Controllers, API routes and Flutter payload builders remain deferred.
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/alk_verification_views.xml",
        "views/alk_config_views.xml",
        "views/res_config_settings_views.xml",
        "views/alk_menus.xml",
    ],
    "assets": {},
    "demo": [],
    "application": True,
    "installable": True,
    "auto_install": False,
}
