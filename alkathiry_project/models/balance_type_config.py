from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AlkBalanceTypeConfig(models.Model):
    """Admin-managed ledger balance types (Mifos X-inspired).

    Lets the admin spin up new wallet balance types directly from the GUI:
    Cumulative, Daily, Periodic, In-Kind, Vouchers, or any custom kind. The
    nightly reset engine (Step 3) consults ``reset_policy`` to decide which
    balances to zero out at the configured cutoff while leaving structural
    periodic allocations intact.
    """

    _name = "alkathiry.balance.type.config"
    _description = "Alkathiry Balance Type Configuration"
    _order = "sequence, name"

    name = fields.Char(string="Balance Type", required=True, translate=True)
    code = fields.Char(string="Technical Code", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    kind = fields.Selection(
        selection=[
            ("cumulative", "Cumulative"),
            ("daily", "Daily"),
            ("periodic", "Periodic"),
            ("in_kind", "In-Kind"),
            ("voucher", "Voucher"),
        ],
        string="Kind",
        required=True,
        default="cumulative",
    )

    reset_policy = fields.Selection(
        selection=[
            ("never", "Never (Cumulative / Structural)"),
            ("daily", "Daily at Cutoff"),
            ("periodic", "Every N Days"),
            ("manual", "Manual Only"),
        ],
        string="Reset Policy",
        required=True,
        default="never",
        help="Drives the nightly reset engine. 'never' protects structural "
        "periodic allocations from being zeroed.",
    )
    reset_period_days = fields.Integer(
        string="Reset Period (days)",
        help="Number of days between resets when the policy is 'periodic'.",
    )

    is_monetary = fields.Boolean(
        string="Monetary",
        default=True,
        help="Monetary balances participate in the double-entry financial core; "
        "in-kind / voucher balances track quantities instead.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    allow_negative = fields.Boolean(string="Allow Negative Balance", default=False)
    default_limit = fields.Float(
        string="Default Limit",
        help="Default cap applied to new wallet balances of this type (0 = unlimited).",
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The balance type code must be unique per company.",
        ),
    ]

    @api.constrains("reset_policy", "reset_period_days")
    def _check_reset_period(self):
        for rec in self:
            if rec.reset_policy == "periodic" and rec.reset_period_days <= 0:
                raise ValidationError(
                    _("A periodic reset policy requires a positive reset period in days.")
                )
