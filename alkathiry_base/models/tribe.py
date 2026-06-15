from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AlkathiryTribe(models.Model):
    """A node in the tribal lineage (nasab) tree.

    This is a proper parent/child/level hierarchy (``_parent_store``) exactly like
    ``spp.area`` is for geography — but for lineage, and deliberately independent
    of any country/region. The trunk is the grand tribe; branches are tribes,
    clans, fakheedahs and families. The same node keeps its identity whether its
    members live in Yemen, Oman, Saudi Arabia or East Asia.
    """

    _name = "alkathiry.tribe"
    _description = "Alkathiry Tribe (Lineage Node)"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "complete_name"
    _rec_name = "complete_name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(index=True, help="Stable unique code for this lineage node.")
    active = fields.Boolean(default=True)

    parent_id = fields.Many2one(
        "alkathiry.tribe",
        string="Parent Tribe",
        ondelete="cascade",
        index=True,
        help="The higher lineage node this one branches from (e.g. a clan's parent "
        "is its tribe).",
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("alkathiry.tribe", "parent_id", string="Sub-tribes")
    complete_name = fields.Char(
        string="Full Lineage",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
    )

    tribe_type_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Level / Type",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:tribe-type')]",
        help="Semantic level: grand tribe / tribe / clan / fakheedah / family. "
        "Admin-managed vocabulary.",
    )
    level = fields.Integer(
        string="Depth",
        compute="_compute_level",
        store=True,
        help="Numeric depth in the tree (0 = trunk).",
    )

    position_ids = fields.One2many(
        "alkathiry.tribe.position", "tribe_id", string="Positions"
    )
    member_count = fields.Integer(compute="_compute_member_count")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The tribe code must be unique."),
    ]

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f"{rec.parent_id.complete_name} / {rec.name}"
            else:
                rec.complete_name = rec.name

    @api.depends("parent_id", "parent_id.level")
    def _compute_level(self):
        for rec in self:
            rec.level = (rec.parent_id.level + 1) if rec.parent_id else 0

    def _compute_member_count(self):
        partner = self.env["res.partner"]
        for rec in self:
            rec.member_count = (
                partner.search_count([("alk_tribe_node_id", "child_of", rec.id)])
                if rec.id
                else 0
            )

    @api.constrains("parent_id")
    def _check_no_cycle(self):
        for rec in self:
            if rec._has_cycle():
                raise ValidationError(_("A tribe cannot be its own ancestor (circular lineage)."))

    def action_view_members(self):
        """Open the individuals whose lineage node is this tribe or a descendant."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Members of %s") % self.name,
            "res_model": "res.partner",
            "view_mode": "list,form",
            "domain": [
                ("is_group", "=", False),
                ("is_registrant", "=", True),
                ("alk_tribe_node_id", "child_of", self.id),
            ],
        }
