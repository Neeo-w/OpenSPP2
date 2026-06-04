from odoo import fields, models


class AlkIdentityToken(models.Model):
    """Secure, encrypted identification token (MOSIP-inspired).

    The local identity engine issues short-lived encrypted tokens (e.g. the JWT
    embedded in the beneficiary's dynamic barcode, or service tokens shared across
    sub-systems). Token material itself is stored encrypted; only metadata needed
    for validation and revocation is kept in clear columns.
    """

    _name = "alkathiry.identity.token"
    _description = "Alkathiry Identity Token"
    _order = "create_date desc"
    _rec_name = "token_uid"

    token_uid = fields.Char(
        string="Token UID",
        required=True,
        index=True,
        help="Opaque public identifier (jti) of the token. Not the secret itself.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Subject",
        required=True,
        ondelete="cascade",
        index=True,
    )
    token_type = fields.Selection(
        selection=[
            ("barcode", "Barcode / Presentation JWT"),
            ("otp", "Redemption OTP"),
            ("session", "Session Token"),
            ("service", "Cross-system Service Token"),
        ],
        string="Type",
        required=True,
        default="barcode",
        index=True,
    )

    # Encrypted payload / secret material (ciphertext only).
    encrypted_payload = fields.Char(string="Encrypted Payload")
    payload_hash = fields.Char(
        string="Payload Hash",
        index=True,
        help="Hash used for constant-time lookup/verification without decrypting.",
    )

    issued_at = fields.Datetime(string="Issued At", default=fields.Datetime.now, required=True)
    expires_at = fields.Datetime(string="Expires At", required=True, index=True)
    state = fields.Selection(
        selection=[
            ("active", "Active"),
            ("consumed", "Consumed"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        default="active",
        required=True,
        index=True,
    )
    consumed_at = fields.Datetime(string="Consumed At")

    # Scope of validity for cross-system use.
    scope = fields.Json(string="Scope", help="Audiences / sub-systems this token is valid for.")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "token_uid_uniq",
            "unique(token_uid)",
            "Identity token UID must be globally unique.",
        ),
    ]
