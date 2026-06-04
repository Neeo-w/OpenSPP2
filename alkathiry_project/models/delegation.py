from odoo import fields, models


class AlkDelegation(models.Model):
    """Beneficiary delegation / proxy (PRD 24.2 ``delegations``, FR-DEL).

    Lets a beneficiary authorise another member (often a family member) to redeem
    on their behalf — once, for a specific service, or permanently. The validation
    engine consults active delegations when a distributor scans a proxy and records
    the originating beneficiary on the resulting transaction
    (``delegated_for_user_id``).
    """

    _name = "alkathiry.delegation"
    _description = "Alkathiry Delegation"
    _order = "create_date desc"

    name = fields.Char(string="Reference", default="New", copy=False, index=True)
    delegator_id = fields.Many2one(
        "res.partner",
        string="Delegator (Beneficiary)",
        required=True,
        ondelete="cascade",
        index=True,
    )
    delegate_id = fields.Many2one(
        "res.partner",
        string="Delegate (Proxy)",
        required=True,
        ondelete="cascade",
        index=True,
    )
    scope = fields.Selection(
        selection=[
            ("once", "Single Use"),
            ("specific_service", "Specific Service"),
            ("permanent", "Permanent"),
        ],
        string="Scope",
        required=True,
        default="once",
    )
    service_id = fields.Many2one(
        "alkathiry.service",
        string="Scoped Service",
        help="Required when scope is 'specific_service'.",
        index=True,
    )
    is_family = fields.Boolean(string="Family Delegation", default=True)
    status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("active", "Active"),
            ("revoked", "Revoked"),
            ("used", "Used"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    approved_by = fields.Many2one("res.users", string="Approved By")
    expires_at = fields.Datetime(string="Expires At", index=True)

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
