from odoo import fields, models


class AlkWalletMovement(models.Model):
    """Per-balance movement history (PRD 24.2.3 ``wallet_movements``).

    Captures every credit, debit and reset-loss against a wallet balance, including
    the nightly-reset losses that the immutable redemption ledger does not record.
    Balance type is resolved dynamically against ``balance.type.config`` rather than
    a fixed enum.
    """

    _name = "alkathiry.wallet.movement"
    _description = "Alkathiry Wallet Movement"
    _order = "id desc"

    wallet_id = fields.Many2one(
        "alkathiry.wallet",
        string="Wallet",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one("res.partner", string="Holder", index=True)
    movement_type = fields.Selection(
        selection=[
            ("credit", "Credit"),
            ("debit", "Debit"),
            ("reset_loss", "Reset Loss"),
        ],
        string="Type",
        required=True,
        index=True,
    )
    amount = fields.Float(required=True)
    balance_type_id = fields.Many2one(
        "alkathiry.balance.type.config",
        string="Balance Type",
        required=True,
        index=True,
    )
    reason = fields.Char()
    performed_by = fields.Many2one("res.users", string="Performed By")
    related_transaction_id = fields.Many2one(
        "alkathiry.transaction",
        string="Related Transaction",
        index=True,
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    def init(self):
        super().init()
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS
                alkathiry_wallet_movement_holder_idx
            ON alkathiry_wallet_movement (partner_id, create_date)
            """
        )
