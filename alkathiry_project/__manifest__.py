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
        "python": [],
    },
    # NOTE: Phase 0 / Step 1 deliverable is the data layer only. Security ACLs,
    # views, controllers, API routes and Flutter payload builders are intentionally
    # deferred until the models are signed off.
    "data": [
        "security/ir.model.access.csv",
    ],
    "assets": {},
    "demo": [],
    "application": True,
    "installable": True,
    "auto_install": False,
}
