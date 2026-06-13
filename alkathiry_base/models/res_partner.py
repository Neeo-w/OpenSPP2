from odoo import api, fields, models


class ResPartner(models.Model):
    """Alkathiry community-profile extension on the registrant.

    IMPORTANT — no duplication: the following already exist in ``spp_registry``
    and are intentionally NOT re-added here (reused as-is):
        * civil_status_id  (marital status, UN marital-status vocabulary)
        * occupation_id    (ISCO-08 occupation)
        * income           (Float)
        * address          (Text)
    This module only adds dimensions that have no existing equivalent, all
    vocabulary-driven so the Central Committee edits the option lists from the UI.
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
        string="Health Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:health-status')]",
        help="General self-declared health condition. Formal disability is handled "
        "separately by spp_disability_registry and is not duplicated here.",
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
        help="Working status (employed/unemployed/student...). Distinct from "
        "occupation_id, which is the ISCO-08 job title.",
    )
    alk_financial_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Financial Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:financial-status')]",
        help="Self-declared economic bracket. Distinct from the numeric income "
        "field and from any computed proxy-means score.",
    )

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
