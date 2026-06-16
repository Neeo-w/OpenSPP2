from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_INDIVIDUAL_DOMAIN = "[('is_registrant', '=', True), ('is_group', '=', False)]"


class AlkathiryOrganization(models.Model):
    """A union / syndicate / organization — a dedicated body, not a registry group.

    Members are individual registrants (people), linked through
    ``alkathiry.organization.member``. Each body is scoped to a country/area and
    can chain a national parent to regional branches. This is deliberately
    separate from the tribal lineage: an organization belongs to its members,
    not to a tribe.
    """

    _name = "alkathiry.organization"
    _description = "Alkathiry Union / Organization"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    code = fields.Char(string="Registration No.", help="Official registration/license number.")

    org_type_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Type",
        required=True,
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:org-type')]",
        help="Union / syndicate, federation, organization, association, cooperative.",
    )
    category_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Specialty",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:org-category')]",
        help="e.g. Engineers, Farmers, Doctors, Health, Agriculture.",
    )

    # Location
    area_id = fields.Many2one(
        "spp.area",
        string="Country / Area",
        index=True,
        help="Where this body operates. The same body can exist per country as a "
        "separate record (e.g. Engineers' Syndicate — Yemen vs — Saudi Arabia).",
    )
    address = fields.Char()
    phone = fields.Char()
    email = fields.Char()
    date_established = fields.Date()

    # Leadership
    president_id = fields.Many2one(
        "res.partner",
        string="President / Responsible",
        domain=_INDIVIDUAL_DOMAIN,
        help="The individual responsible for this body (e.g. the union president).",
    )

    # National -> regional hierarchy (optional, within the same org family)
    parent_id = fields.Many2one(
        "alkathiry.organization",
        string="Parent Body",
        ondelete="restrict",
        help="Higher body this one is a branch of (e.g. a regional branch under "
        "the national syndicate).",
    )
    child_ids = fields.One2many("alkathiry.organization", "parent_id", string="Branches")

    # Members (people)
    member_ids = fields.One2many(
        "alkathiry.organization.member",
        "organization_id",
        string="Members",
    )
    member_count = fields.Integer(compute="_compute_member_count")

    notes = fields.Text()

    @api.depends("member_ids", "member_ids.active")
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.member_ids.filtered("active"))

    @api.constrains("parent_id")
    def _check_no_cycle(self):
        for rec in self:
            parent = rec.parent_id
            seen = {rec.id}
            while parent:
                if parent.id in seen:
                    raise ValidationError(_("An organization cannot be its own parent (circular hierarchy)."))
                seen.add(parent.id)
                parent = parent.parent_id

    def action_view_members(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Members of %s") % self.name,
            "res_model": "alkathiry.organization.member",
            "view_mode": "list,form",
            "domain": [("organization_id", "=", self.id)],
            "context": {"default_organization_id": self.id},
        }


class AlkathiryOrganizationMember(models.Model):
    """Membership of an individual in a union / organization, with role and dates."""

    _name = "alkathiry.organization.member"
    _description = "Alkathiry Organization Member"
    _order = "organization_id, role_id, id"
    _rec_name = "partner_id"

    organization_id = fields.Many2one(
        "alkathiry.organization",
        string="Organization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Member",
        required=True,
        ondelete="cascade",
        index=True,
        domain=_INDIVIDUAL_DOMAIN,
    )
    role_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Role",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:org-role')]",
    )
    membership_no = fields.Char(string="Membership No.")
    date_join = fields.Date(default=fields.Date.context_today)
    date_end = fields.Date()
    active = fields.Boolean(default=True)

    # Convenience related fields for display on the citizen profile.
    org_type_id = fields.Many2one(related="organization_id.org_type_id", string="Type", store=True)
    org_area_id = fields.Many2one(related="organization_id.area_id", string="Country / Area", store=True)

    _sql_constraints = [
        (
            "uniq_member",
            "unique(organization_id, partner_id)",
            "This person is already a member of this organization.",
        ),
    ]

    @api.constrains("date_join", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_join and rec.date_end and rec.date_end < rec.date_join:
                raise ValidationError(_("End date cannot be earlier than the join date."))
