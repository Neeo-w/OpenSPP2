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
        ],
        string="Community Status",
        default="draft",
        index=True,
        help="Dynamic-workflow status consulted by the validation engine "
        "(FR-DIS-03 #1: beneficiary must be active).",
    )

    # Geographic placement used for scope matching of verifiers and allocations.
    alk_neighborhood = fields.Char(string="Neighborhood")
    alk_tribe = fields.Char(string="Tribe / Sub-tribe")
    alk_region_id = fields.Many2one("res.country.state", string="Region", index=True)

    alk_wallet_ids = fields.One2many("alkathiry.wallet", "partner_id", string="Wallets")
    alk_identity_token_ids = fields.One2many(
        "alkathiry.identity.token", "partner_id", string="Identity Tokens"
    )
