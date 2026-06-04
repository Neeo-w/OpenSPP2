from odoo import api, fields, models


class AlkGeoArea(models.Model):
    """Dynamic, self-referencing geographic / tribal hierarchy.

    The PRD references fixed ``tribes`` and ``districts`` tables. To honour the
    Absolute Dynamism mandate these are replaced by a single configurable tree:
    the admin defines arbitrary area *levels* (region → district → tribe →
    sub-tribe → neighborhood, or any other structure) and arbitrary nodes, with no
    hardcoded depth. Verifier scopes, beneficiary placement, service targeting and
    regional filtering all resolve against this tree.
    """

    _name = "alkathiry.geo.area"
    _description = "Alkathiry Geographic / Tribal Area"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "complete_name"
    _rec_name = "complete_name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string="Technical Code", required=True)
    # Area kind is itself admin-managed so the hierarchy depth/labels are dynamic.
    level_id = fields.Many2one(
        "alkathiry.geo.area.level",
        string="Area Level",
        required=True,
        index=True,
        help="Dynamic level (e.g. Region, District, Tribe, Neighborhood).",
    )
    parent_id = fields.Many2one(
        "alkathiry.geo.area",
        string="Parent Area",
        ondelete="cascade",
        index=True,
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("alkathiry.geo.area", "parent_id", string="Sub-areas")
    complete_name = fields.Char(
        string="Full Path",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The area code must be unique per company.",
        ),
    ]

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f"{rec.parent_id.complete_name} / {rec.name}"
            else:
                rec.complete_name = rec.name


class AlkGeoAreaLevel(models.Model):
    """Admin-defined level of the geographic hierarchy (e.g. Region, Tribe)."""

    _name = "alkathiry.geo.area.level"
    _description = "Alkathiry Geographic Area Level"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string="Technical Code", required=True)
    sequence = fields.Integer(default=10, help="Depth order: lower is higher in the tree.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The area level code must be unique per company.",
        ),
    ]
