from odoo import fields, models


class AlkHealthCondition(models.Model):
    """A medical condition / disease recorded for an individual, with proof.

    Complements ``spp_disability_registry`` (which models *functional* disability
    via Washington-Group assessments) by capturing *diseases* (diabetes,
    hypertension, thalassemia...) together with the supporting medical documents
    the citizen uploads at registration.
    """

    _name = "alkathiry.health.condition"
    _description = "Alkathiry Health Condition"
    _order = "diagnosis_date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Individual",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('is_group', '=', False), ('is_registrant', '=', True)]",
    )
    disease_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Disease / Condition",
        required=True,
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:disease')]",
    )
    diagnosis_date = fields.Date(string="Diagnosis Date")
    status = fields.Selection(
        selection=[
            ("active", "Active"),
            ("chronic", "Chronic"),
            ("under_treatment", "Under Treatment"),
            ("recovered", "Recovered"),
        ],
        default="active",
        required=True,
    )
    severity = fields.Selection(
        selection=[
            ("mild", "Mild"),
            ("moderate", "Moderate"),
            ("severe", "Severe"),
        ],
    )
    notes = fields.Text()
    # Health proof documents uploaded by/for the citizen.
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "alkathiry_health_condition_attachment_rel",
        "condition_id",
        "attachment_id",
        string="Medical Proof",
    )
    attachment_count = fields.Integer(compute="_compute_attachment_count")

    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)
