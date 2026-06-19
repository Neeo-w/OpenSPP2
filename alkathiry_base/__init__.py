from . import models
from . import wizards


def pre_init_hook(env):
    """Clean up before re-typing the lineage onto registry groups.

    The standalone ``alkathiry.tribe`` model is removed: the tribe node is now a
    registry group (``res.partner``). Two columns that used to reference
    ``alkathiry.tribe`` are re-typed to ``res.partner`` during this upgrade —
    ``res_partner.alk_tribe_node_id`` and ``alkathiry_tribe_position.tribe_id``.
    Their existing integer values point at old alkathiry.tribe ids, which would
    violate the new foreign keys, so we clear them first.

    This is also a no-op on a clean install (the columns/tables don't exist yet),
    and it removes any stale external ids left by the previously separate
    ``alkathiry_tribe`` module.

    The destructive cleanup is GUARDED on the old ``alkathiry.tribe`` model still
    being registered in ``ir_model``: it runs only during the one upgrade that
    removes that model, never on later upgrades (which would otherwise wipe the
    lineage links and positions that have since been entered).
    """
    cr = env.cr

    # Only perform the one-time migration cleanup while the removed model is still
    # registered. Once Odoo drops the orphan ir_model row, later upgrades skip this.
    cr.execute("SELECT 1 FROM ir_model WHERE model = 'alkathiry.tribe' LIMIT 1")
    migrating = bool(cr.fetchone())

    if migrating:
        # Clear stale lineage-node references on individuals (FK retargets to res.partner).
        cr.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'res_partner' AND column_name = 'alk_tribe_node_id'
            """
        )
        if cr.fetchone():
            cr.execute("UPDATE res_partner SET alk_tribe_node_id = NULL")

        # Drop old position rows whose tribe_id pointed at alkathiry.tribe ids.
        cr.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'alkathiry_tribe_position'
            """
        )
        if cr.fetchone():
            cr.execute("DELETE FROM alkathiry_tribe_position")

    # Remove stale external ids for the now-removed alkathiry.tribe model
    # (whether registered by the old alkathiry_tribe module or alkathiry_base).
    env["ir.model.data"].search(
        [("model", "=", "ir.model"), ("name", "=", "model_alkathiry_tribe")]
    ).unlink()

    # Unions/organizations moved from registry groups + position tracks to the
    # dedicated alkathiry.organization model. Clear references to the vocabulary
    # codes that are being removed, so Odoo's end-of-load orphan cleanup can
    # delete them without hitting a foreign-key violation.
    # Only the group-based union/organization TYPES are gone for good (bodies are
    # dedicated now). The ladder tracks and leadership titles were kept — the
    # generic ladder engine uses them — so they are NOT in this list.
    removed_codes = [
        "code_group_type_union",
        "code_group_type_organization",
        "code_group_type_activity",
    ]
    imd = env["ir.model.data"].search(
        [
            ("module", "=", "alkathiry_base"),
            ("model", "=", "spp.vocabulary.code"),
            ("name", "in", removed_codes),
        ]
    )
    code_ids = imd.mapped("res_id")
    if code_ids:
        # Groups that were typed with the deprecated union/organization types.
        cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'res_partner' AND column_name = 'group_type_id'"
        )
        if cr.fetchone():
            cr.execute(
                "UPDATE res_partner SET group_type_id = NULL WHERE group_type_id = ANY(%s)",
                (code_ids,),
            )
        # Any position rows that used the deprecated union/org tracks or roles.
        cr.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'alkathiry_tribe_position'"
        )
        if cr.fetchone():
            cr.execute(
                "DELETE FROM alkathiry_tribe_position "
                "WHERE track_id = ANY(%s) OR position_id = ANY(%s)",
                (code_ids, code_ids),
            )
