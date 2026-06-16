from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerLineage(models.Model):
    """Tribal lineage hierarchy carried directly on the registry Group.

    A tribe node IS a registry group (``res.partner`` with ``is_group=True``),
    so it shows up natively in *Browse All Groups* and reuses the group type,
    membership and registry features. On top of that we add a single-parent
    lineage chain — the same dynamic pattern ``spp.area`` uses for geography
    (parent / complete name / level / materialized path) — so the same node
    keeps its identity across countries.

    ``res.partner`` already owns the native ``parent_id`` hierarchy (contacts/
    companies), so a second ``_parent_store`` is not possible. We therefore
    maintain the lineage path ourselves through stored recursive computes —
    still fully dynamic, just not via the native mechanism.
    """

    _inherit = "res.partner"

    # Single lineage parent (e.g. a clan's parent is its tribe). This is the
    # "Parent Tribe" field — now living on the group itself, wired into the
    # group form and Browse All Groups.
    alk_lineage_parent_id = fields.Many2one(
        "res.partner",
        string="Parent Tribe",
        domain="[('is_group', '=', True), ('is_registrant', '=', True)]",
        index=True,
        ondelete="restrict",
        help="The higher lineage node this group branches from (grand tribe > "
        "tribe > batn > clan > fakheedah > family).",
    )
    alk_lineage_child_ids = fields.One2many(
        "res.partner",
        "alk_lineage_parent_id",
        string="Sub-tribes",
    )
    # Materialized path of ids ("3/8/15/") — our manual equivalent of
    # spp.area.parent_path; enables fast subtree and ancestor resolution.
    alk_lineage_path = fields.Char(
        compute="_compute_alk_lineage_path",
        recursive=True,
        store=True,
        index=True,
    )
    alk_lineage_complete_name = fields.Char(
        string="Full Lineage",
        compute="_compute_alk_lineage_complete_name",
        recursive=True,
        store=True,
    )
    alk_lineage_level = fields.Integer(
        string="Lineage Depth",
        compute="_compute_alk_lineage_level",
        store=True,
        help="Numeric depth in the lineage tree (0 = grand tribe / root).",
    )
    # Positions held at this node (tribe x area -> position + official).
    alk_position_ids = fields.One2many(
        "alkathiry.tribe.position",
        "tribe_id",
        string="Tribal Positions",
    )
    alk_lineage_member_count = fields.Integer(
        string="Lineage Members",
        compute="_compute_alk_lineage_member_count",
    )

    @api.depends("alk_lineage_parent_id", "alk_lineage_parent_id.alk_lineage_path")
    def _compute_alk_lineage_path(self):
        for rec in self:
            if rec.alk_lineage_parent_id and rec.alk_lineage_parent_id.alk_lineage_path:
                rec.alk_lineage_path = f"{rec.alk_lineage_parent_id.alk_lineage_path}{rec.id}/"
            elif rec.id:
                rec.alk_lineage_path = f"{rec.id}/"
            else:
                rec.alk_lineage_path = False

    @api.depends("name", "alk_lineage_parent_id.alk_lineage_complete_name")
    def _compute_alk_lineage_complete_name(self):
        for rec in self:
            parent = rec.alk_lineage_parent_id
            if parent and parent.alk_lineage_complete_name:
                rec.alk_lineage_complete_name = f"{parent.alk_lineage_complete_name} / {rec.name or ''}"
            else:
                rec.alk_lineage_complete_name = rec.name or False

    @api.depends("alk_lineage_parent_id", "alk_lineage_parent_id.alk_lineage_level")
    def _compute_alk_lineage_level(self):
        for rec in self:
            parent = rec.alk_lineage_parent_id
            rec.alk_lineage_level = (parent.alk_lineage_level + 1) if parent else 0

    def _compute_alk_lineage_member_count(self):
        partner = self.env["res.partner"]
        for rec in self:
            if rec.alk_lineage_path:
                rec.alk_lineage_member_count = partner.search_count(
                    [("alk_tribe_node_id.alk_lineage_path", "=like", f"{rec.alk_lineage_path}%")]
                )
            else:
                rec.alk_lineage_member_count = 0

    @api.constrains("alk_lineage_parent_id")
    def _check_alk_lineage_no_cycle(self):
        for rec in self:
            parent = rec.alk_lineage_parent_id
            seen = {rec.id}
            while parent:
                if parent.id in seen:
                    raise ValidationError(
                        _("A tribe cannot be its own ancestor (circular lineage).")
                    )
                seen.add(parent.id)
                parent = parent.alk_lineage_parent_id

    def action_alk_view_lineage_members(self):
        """Open the individuals whose lineage node is this group or a descendant."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Members of %s") % self.name,
            "res_model": "res.partner",
            "view_mode": "list,form",
            "domain": [
                ("is_group", "=", False),
                ("is_registrant", "=", True),
                ("alk_tribe_node_id.alk_lineage_path", "=like", f"{self.alk_lineage_path or ''}%"),
            ],
        }
