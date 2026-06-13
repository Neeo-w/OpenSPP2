from odoo import api, fields, models


class ResPartner(models.Model):
    """Alkathiry community-profile extension on the registrant.

    All additions are vocabulary-driven so the Central Committee can edit the
    option lists (blood types, education levels, statuses, positions...) from the
    Odoo UI without code — consistent with the OpenSPP vocabularies scenario.
    The formal hierarchy links remain the native OpenSPP ones (``area_id`` from
    spp_area, and ``spp.group.membership`` for the tribal tree); the fields here
    only add demographics and a denormalized convenience pointer.
    """

    _inherit = "res.partner"

    # --- System identifier (concept borrowed from OpenG2P ``unique_id``) ---
    alk_citizen_no = fields.Char(
        string="Citizen No.",
        index=True,
        copy=False,
        readonly=True,
        help="System-generated unique community number for the individual.",
    )

    # --- Hierarchy link (convenience pointer; source of truth is membership) ---
    alk_tribe_id = fields.Many2one(
        "res.partner",
        string="Tribe / Group",
        domain="[('is_group', '=', True), ('is_registrant', '=', True)]",
        index=True,
        help="Denormalized pointer to the tribal/family group node the individual "
        "belongs to. The authoritative membership is stored in spp.group.membership.",
    )

    # --- Address & free-form ---
    alk_address_detail = fields.Text(string="Detailed Address")
    alk_additional_info = fields.Text(string="Additional Information")

    # --- Demographic / socio-economic (vocabulary-driven, admin-editable) ---
    alk_marital_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Marital Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:marital-status')]",
    )
    alk_blood_type_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Blood Type",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:blood-type')]",
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
    alk_health_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Health Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:health-status')]",
    )
    alk_financial_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Financial Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:financial-status')]",
    )
    alk_occupation = fields.Char(string="Occupation")
    alk_monthly_income = fields.Float(string="Monthly Income")

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
