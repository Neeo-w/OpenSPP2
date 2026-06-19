from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DocLevel(models.Model):
    """A generic certification stage — the single hierarchy engine.

    ONE container serves every structure: its ``kind`` (position / department /
    committee / region / custom) is just a label chosen by the Secretary General.
    Whatever the kind, the hierarchical option is always present: an order
    (``sequence``), a next-higher stage (``parent_level_id``), and a set of
    members (``documenter_ids``) the beneficiary picks one of. ``_parent_store``
    over ``parent_level_id`` powers the top-down org-chart view, and a stage can be
    optionally bound to a place (``spp.area``), a committee
    (``alkathiry.organization``), a job or a department (lightweight vocabularies).
    """

    _name = "doc.level"
    _description = "Certification Level (Stage)"
    _parent_name = "parent_level_id"
    _parent_store = True
    _order = "sequence, id"

    KIND_SELECTION = [
        ("position", "Position"),
        ("department", "Department"),
        ("committee", "Committee"),
        ("region", "Region"),
        ("custom", "Custom"),
    ]

    name = fields.Char(required=True)
    hierarchy_id = fields.Many2one(
        "doc.hierarchy",
        string="Hierarchy",
        ondelete="cascade",
        index=True,
        help="Owning hierarchy. Empty for a shared global stage (Secretary "
        "General and his committees).",
    )
    country_id = fields.Many2one(related="hierarchy_id.country_id", store=True, index=True)
    sequence = fields.Integer(default=10, help="Mandatory order in the ladder.")
    kind = fields.Selection(KIND_SELECTION, required=True, default="position")
    is_global = fields.Boolean(
        string="Shared / Global",
        help="A fixed stage shared by every hierarchy (the common top).",
    )
    parent_level_id = fields.Many2one(
        "doc.level",
        string="Reports To (Next Level)",
        ondelete="restrict",
        index=True,
        help="The next-higher stage the request escalates to.",
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("doc.level", "parent_level_id", string="Lower Levels")

    # --- optional classifications (all reused from existing infrastructure) ---
    geo_level = fields.Selection(
        [("country", "Country"), ("region", "Region"), ("city", "City"), ("area", "Area")],
        string="Geographic Level",
        help="If set, members are filtered so their place contains the beneficiary's.",
    )
    area_id = fields.Many2one("spp.area", string="Place", index=True)
    committee_id = fields.Many2one("alkathiry.organization", string="Committee")
    job_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Job / Position",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:job')]",
    )
    department_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Department",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:department')]",
    )

    documenter_ids = fields.One2many("doc.documenter", "level_id", string="Members")
    documenter_count = fields.Integer(compute="_compute_documenter_count")

    @api.depends("documenter_ids", "documenter_ids.active")
    def _compute_documenter_count(self):
        for rec in self:
            rec.documenter_count = len(rec.documenter_ids.filtered("active"))

    @api.constrains("parent_level_id")
    def _check_no_level_cycle(self):
        for rec in self:
            if rec._has_cycle():
                raise ValidationError(_("A level cannot report to itself (circular chain)."))

    def eligible_documenters(self, citizen_area=None):
        """Active members of this level, optionally filtered so the member's place
        contains the beneficiary's place (used by the route builder)."""
        self.ensure_one()
        members = self.documenter_ids.filtered("active")
        if self.geo_level and citizen_area and citizen_area.parent_path:
            members = members.filtered(
                lambda m: m.area_id
                and m.area_id.parent_path
                and citizen_area.parent_path.startswith(m.area_id.parent_path)
            )
        return members


class DocDocumenter(models.Model):
    """A member assigned to a level, with a role. Flexible classification.

    The same person can be a manager in one level and a member in another. The
    holder is a person (``partner_id``) optionally matched to a system user
    (``user_id``, used to drive the workflow and access rules). Classifications
    (place, job, department, committee) are all optional and reuse existing models.
    """

    _name = "doc.documenter"
    _description = "Certification Member (Documenter)"
    _order = "level_id, role_id, id"
    _rec_name = "partner_id"

    level_id = fields.Many2one("doc.level", string="Level", required=True, ondelete="cascade", index=True)
    hierarchy_id = fields.Many2one(related="level_id.hierarchy_id", store=True, index=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Member",
        required=True,
        index=True,
        domain="[('is_registrant', '=', True), ('is_group', '=', False)]",
    )
    user_id = fields.Many2one(
        "res.users",
        string="System User",
        index=True,
        help="The login that acts on requests for this member (accept / reject / "
        "escalate). Required for the member to process requests.",
    )
    role_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Role",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:doc-role')]",
        help="manager / member / assistant / employee.",
    )
    area_id = fields.Many2one("spp.area", string="Place")
    job_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Job / Position",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:job')]",
    )
    department_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Department",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:department')]",
    )
    committee_id = fields.Many2one("alkathiry.organization", string="Committee")
    active = fields.Boolean(default=True)
