from odoo import fields, models


class AlkCredentialTemplate(models.Model):
    """Dynamic credential / document template (Sunbird RC-inspired).

    The admin defines templates that parse database parameters at issuance time to
    build certified digital assets — donation certificates, tribal recognition
    credentials, verifier digital signatures and seals — without code changes. The
    schema and layout are stored as metadata and rendered dynamically.
    """

    _name = "alkathiry.credential.template"
    _description = "Alkathiry Credential Template"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string="Technical Code", required=True)
    active = fields.Boolean(default=True)
    credential_type = fields.Selection(
        selection=[
            ("donation_certificate", "Donation Certificate"),
            ("recognition", "Tribal Recognition Credential"),
            ("verifier_signature", "Verifier Digital Signature"),
            ("seal", "Official Seal"),
            ("custom", "Custom"),
        ],
        string="Credential Type",
        required=True,
        default="custom",
    )

    # JSON schema describing the data fields the credential binds.
    schema = fields.Json(string="Attribute Schema")
    # Layout/markup template (e.g. QWeb/HTML/SVG reference) rendered with bound data.
    layout_template = fields.Text(string="Layout Template")
    # Signing / sealing configuration (key alias, algorithm) — secrets kept elsewhere.
    signing_config = fields.Json(string="Signing Configuration")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The credential template code must be unique per company.",
        ),
    ]


class AlkCredential(models.Model):
    """An issued credential instance written to the beneficiary storage layout."""

    _name = "alkathiry.credential"
    _description = "Alkathiry Issued Credential"
    _order = "issued_at desc"

    name = fields.Char(string="Reference", required=True, copy=False, default="New", index=True)
    reference_number = fields.Char(string="Certificate Number", copy=False, index=True)
    template_id = fields.Many2one(
        "alkathiry.credential.template",
        string="Template",
        required=True,
        ondelete="restrict",
        index=True,
    )
    credential_type = fields.Selection(
        selection=[
            ("membership", "Membership"),
            ("donation", "Donation"),
            ("beneficiary", "Beneficiary"),
            ("identification", "Identification"),
        ],
        string="Certificate Type",
        index=True,
    )
    provider_id = fields.Many2one("alkathiry.service.provider", string="Issuing Provider")
    partner_id = fields.Many2one(
        "res.partner",
        string="Holder",
        required=True,
        ondelete="cascade",
        index=True,
    )
    # Bound attribute values resolved from the database at issuance.
    payload = fields.Json(string="Bound Attributes")
    rendered_document = fields.Binary(string="Rendered Document", attachment=True)
    pdf_url = fields.Char(string="Document URL")
    signed_by = fields.Many2one("res.users", string="Signed By")
    signature = fields.Char(string="Digital Signature")
    sent_to_email = fields.Boolean(string="Sent to Email", default=False)
    issued_at = fields.Datetime(string="Issued At", default=fields.Datetime.now)
    valid_until = fields.Datetime(string="Valid Until")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("revoked", "Revoked"),
        ],
        default="draft",
        required=True,
        index=True,
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
