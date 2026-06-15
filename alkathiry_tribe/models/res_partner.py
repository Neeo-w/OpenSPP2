from odoo import api, fields, models


class ResPartner(models.Model):
    """Link the individual to the lineage tree and resolve their representatives.

    This replaces the ambiguous group-membership pointer for *lineage*: the
    citizen points to a clean ``alkathiry.tribe`` node, and the responsible
    officials are resolved by intersecting that lineage node with the citizen's
    geographic area against the positions matrix.
    """

    _inherit = "res.partner"

    alk_tribe_node_id = fields.Many2one(
        "alkathiry.tribe",
        string="Lineage Node",
        index=True,
        help="The citizen's node in the tribal lineage tree (e.g. their family or "
        "fakheedah). Independent of where they currently live.",
    )
    alk_representative_ids = fields.Many2many(
        "res.users",
        string="Tribal Representatives",
        compute="_compute_alk_representatives",
        help="Officials resolved from the positions matrix by intersecting this "
        "individual's lineage node with their residential area.",
    )

    @api.depends("alk_tribe_node_id", "area_id")
    def _compute_alk_representatives(self):
        positions_model = self.env["alkathiry.tribe.position"]
        for rec in self:
            users = self.env["res.users"].browse()
            if rec.alk_tribe_node_id:
                # Positions whose lineage node is this node or an ancestor.
                positions = positions_model.search(
                    [
                        ("tribe_id", "parent_of", rec.alk_tribe_node_id.id),
                        ("active", "=", True),
                    ]
                )
                positions = positions.filtered(
                    lambda p, rec=rec: rec._alk_position_covers_area(p)
                )
                users = positions.mapped("user_id")
            rec.alk_representative_ids = users

    def _alk_position_covers_area(self, position):
        """A position covers the citizen if it has no area scope, or its area is
        the citizen's residential area or an ancestor of it."""
        self.ensure_one()
        if not position.area_id:
            return True
        citizen_area = self.area_id
        if citizen_area and citizen_area.parent_path and position.area_id.parent_path:
            return citizen_area.parent_path.startswith(position.area_id.parent_path)
        return False
