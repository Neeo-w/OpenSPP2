from odoo import api, fields, models


class ResPartner(models.Model):
    """Alkathiry community-profile extension on the registrant.

    IMPORTANT — no duplication: civil_status_id, occupation_id, income and address
    already exist in ``spp_registry`` and are reused as-is. Disability (functional,
    Washington-Group) is handled by ``spp_disability_registry``; this module adds
    a separate *medical conditions / diseases* record with proof attachments.
    """

    _inherit = "res.partner"

    # --- System identifier (no equivalent in spp; concept from OpenG2P unique_id) ---
    alk_citizen_no = fields.Char(
        string="Citizen No.",
        index=True,
        copy=False,
        readonly=True,
        help="System-generated unique community number for the individual.",
    )

    # --- Tribal link (convenience pointer; source of truth is spp.group.membership) ---
    alk_tribe_id = fields.Many2one(
        "res.partner",
        string="Tribe / Group",
        domain="[('is_group', '=', True), ('is_registrant', '=', True)]",
        index=True,
        help="Denormalized pointer to the tribal/family group node the individual "
        "belongs to. The authoritative membership is spp.group.membership.",
    )

    # --- New demographic / socio-economic dimensions (vocabulary-driven) ---
    alk_blood_type_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Blood Type",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:blood-type')]",
    )
    alk_health_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="General Health Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:health-status')]",
    )
    alk_education_level_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Education Level",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:education-level')]",
    )
    alk_employment_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Employment Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:employment-status')]",
    )
    alk_financial_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Financial Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:financial-status')]",
    )

    # --- Medical conditions / diseases (with proof attachments) ---
    alk_health_condition_ids = fields.One2many(
        "alkathiry.health.condition",
        "partner_id",
        string="Medical Conditions",
    )
    alk_health_condition_count = fields.Integer(
        compute="_compute_alk_health_condition_count",
    )

    # --- Responsible local official(s), resolved by the smallest residential area ---
    alk_responsible_user_ids = fields.Many2many(
        "res.users",
        string="Responsible Officials",
        compute="_compute_alk_responsible_users",
        help="Local users (e.g. the neighborhood Aqil) whose assigned area covers "
        "this individual's residential area (area_id). Resolved directly from the "
        "smallest residential unit, independent of the verification-chain length.",
    )

    @api.depends("alk_health_condition_ids")
    def _compute_alk_health_condition_count(self):
        for rec in self:
            rec.alk_health_condition_count = len(rec.alk_health_condition_ids)

    @api.depends("area_id")
    def _compute_alk_responsible_users(self):
        users_model = self.env["res.users"]
        for rec in self:
            if rec.area_id:
                # Users whose assigned area (center_area_ids) is an ancestor or the
                # area itself => they cover this citizen's residential area.
                rec.alk_responsible_user_ids = users_model.search(
                    [("center_area_ids", "parent_of", rec.area_id.id)]
                )
            else:
                rec.alk_responsible_user_ids = users_model.browse()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Assign a citizen number to individual registrants only.
            if (
                vals.get("is_registrant")
                and not vals.get("is_group")
                and not vals.get("alk_citizen_no")
            ):
                seq = self.env["ir.sequence"].next_by_code("alkathiry.citizen")
                if seq:
                    vals["alk_citizen_no"] = seq
        return super().create(vals_list)
