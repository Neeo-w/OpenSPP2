from odoo import _, fields, models


class AlkathiryPositionClone(models.TransientModel):
    """Clone a whole ladder (a root node + all its subordinates) to another country.

    Replicates the structure — titles, levels and reporting links — so the same
    ladder can be re-used per country (e.g. the Al-Kathir sheikhs ladder in Yemen
    cloned to Saudi Arabia). By default the holders are cleared, leaving the new
    ladder ready for officials to be appointed.
    """

    _name = "alkathiry.position.clone"
    _description = "Clone Ladder to Another Country"

    source_position_id = fields.Many2one(
        "alkathiry.tribe.position",
        string="Ladder Root to Clone",
        required=True,
    )
    target_area_id = fields.Many2one(
        "spp.area",
        string="Target Country / Place",
        required=True,
        help="The new place every cloned node will be set to.",
    )
    keep_holders = fields.Boolean(
        string="Keep assigned holders",
        default=False,
        help="Off (default) clears holders so the new ladder is ready for appointments.",
    )

    def action_clone(self):
        self.ensure_one()
        defaults = {"area_id": self.target_area_id.id, "active": True}
        if not self.keep_holders:
            defaults.update({"partner_id": False, "user_id": False})
        new_root = self.source_position_id.copy_subtree(defaults=defaults)
        return {
            "type": "ir.actions.act_window",
            "name": _("Cloned Ladder"),
            "res_model": "alkathiry.tribe.position",
            "view_mode": "hierarchy,list,form",
            "domain": [("id", "child_of", new_root.id)],
            "context": {"search_default_g_track": 0},
        }
