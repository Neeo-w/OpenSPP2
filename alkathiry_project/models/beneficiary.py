from odoo import fields, models


class ResPartner(models.Model):
    """Beneficiary / community-member profile extension.

    Reuses Odoo's ``res.partner`` as the registrant record (OpenSPP convention) and
    layers the dynamic, metadata-driven community attributes on top. Category-defined
    custom fields are stored polymorphically in ``alk_dynamic_values`` rather than as
    hardcoded columns, preserving absolute dynamism.
    """

    _inherit = "res.partner"

    alk_is_beneficiary = fields.Boolean(string="Is Community Beneficiary", default=False, index=True)
    alk_category_id = fields.Many2one(
        "alkathiry.dynamic.category",
        string="Community Category",
        index=True,
    )
    # Values for the category's dynamic registration fields, keyed by field key.
    alk_dynamic_values = fields.Json(string="Dynamic Profile Values")

    alk_status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("under_verification", "Under Verification"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("rejected", "Rejected"),
            ("deceased", "Deceased"),
            ("archived", "Archived"),
        ],
        string="Community Status",
        default="draft",
        index=True,
        help="Dynamic-workflow status consulted by the validation engine "
        "(FR-DIS-03 #1: beneficiary must be active).",
    )

    # Geographic placement against the dynamic hierarchy (replaces fixed
    # tribe_id / district_id columns from the PRD users table).
    alk_area_id = fields.Many2one(
        "alkathiry.geo.area",
        string="Geographic / Tribal Area",
        index=True,
    )
    alk_assigned_aqil_id = fields.Many2one(
        "res.users",
        string="Assigned Aqil",
        help="First-tier verifier responsible for this beneficiary.",
    )

    # Demographic / lifecycle attributes (PRD users table).
    alk_birth_date = fields.Date(string="Birth Date")
    alk_gender = fields.Selection(
        selection=[("male", "Male"), ("female", "Female")],
        string="Gender",
    )
    alk_marital_status = fields.Char(string="Marital Status")
    alk_family_count = fields.Integer(string="Family Count", default=1)
    alk_device_token_fcm = fields.Char(string="FCM Device Token")
    # National ID kept hashed + encrypted (never in clear), per security spec.
    alk_national_id_hash = fields.Char(string="National ID Hash", index=True)
    alk_national_id_enc = fields.Char(string="National ID (Encrypted)")
    alk_activated_at = fields.Datetime(string="Activated At")
    alk_deceased_at = fields.Datetime(string="Deceased At")

    alk_wallet_ids = fields.One2many("alkathiry.wallet", "partner_id", string="Wallets")
    alk_identity_token_ids = fields.One2many(
        "alkathiry.identity.token", "partner_id", string="Identity Tokens"
    )
    alk_delegation_given_ids = fields.One2many(
        "alkathiry.delegation", "delegator_id", string="Delegations Granted"
    )
