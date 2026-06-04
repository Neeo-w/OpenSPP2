import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AlkWallet(models.Model):
    """A beneficiary (or actor) wallet holding one balance per configured type.

    Backend wallet container for the Mifos X-inspired double-entry core. Actual
    monetary movements live in the immutable ``alkathiry.transaction`` ledger; the
    cached balances here are derived for fast eligibility checks.
    """

    _name = "alkathiry.wallet"
    _description = "Alkathiry Wallet"
    _order = "partner_id"

    name = fields.Char(compute="_compute_name", store=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Holder",
        required=True,
        ondelete="cascade",
        index=True,
    )
    balance_ids = fields.One2many("alkathiry.balance", "wallet_id", string="Balances")
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    @api.depends("partner_id.name")
    def _compute_name(self):
        for rec in self:
            rec.name = _("Wallet: %s", rec.partner_id.display_name or "")


class AlkBalance(models.Model):
    """A single balance bucket of a given type within a wallet.

    ``available_amount`` is consumed by the validation engine (FR-DIS-03 #4 —
    unspent quota within the current reset window) and reset by the nightly engine
    according to the balance type's ``reset_policy``.
    """

    _name = "alkathiry.balance"
    _description = "Alkathiry Wallet Balance"
    _order = "wallet_id, balance_type_id"

    wallet_id = fields.Many2one(
        "alkathiry.wallet",
        string="Wallet",
        required=True,
        ondelete="cascade",
        index=True,
    )
    balance_type_id = fields.Many2one(
        "alkathiry.balance.type.config",
        string="Balance Type",
        required=True,
        index=True,
    )
    current_amount = fields.Float(string="Current Amount", default=0.0)
    reserved_amount = fields.Float(string="Reserved Amount", default=0.0)
    available_amount = fields.Float(
        string="Available Amount",
        compute="_compute_available",
        store=True,
    )
    limit_amount = fields.Float(string="Limit", default=0.0, help="0 = unlimited.")
    last_reset_at = fields.Datetime(string="Last Reset At")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    @api.depends("current_amount", "reserved_amount")
    def _compute_available(self):
        for rec in self:
            rec.available_amount = rec.current_amount - rec.reserved_amount

    _sql_constraints = [
        (
            "wallet_type_uniq",
            "unique(wallet_id, balance_type_id)",
            "A wallet holds a single balance per balance type.",
        ),
    ]

    # ------------------------------------------------------------------
    # Nightly reset engine (Step 3)
    # ------------------------------------------------------------------
    def _do_reset(self, reason="daily"):
        """Zero the balance, logging the lost amount as a reset_loss movement."""
        self.ensure_one()
        lost = self.current_amount
        if lost:
            self.env["alkathiry.wallet.movement"].sudo().create(
                {
                    "wallet_id": self.wallet_id.id,
                    "partner_id": self.wallet_id.partner_id.id,
                    "movement_type": "reset_loss",
                    "amount": lost,
                    "balance_type_id": self.balance_type_id.id,
                    "reason": _("Balance reset (%s)") % reason,
                }
            )
        self.write({"current_amount": 0.0, "last_reset_at": fields.Datetime.now()})

    @api.model
    def _cron_reset_balances(self):
        """Evaluate each balance against its type's reset policy.

        Daily balances are zeroed once per day; periodic balances every N days;
        'never'/'manual' (structural periodic allocations) are left intact. The
        per-type policy makes the behaviour fully configurable.
        """
        now = fields.Datetime.now()
        balances = self.search([])
        for bal in balances:
            balance_type = bal.balance_type_id
            policy = balance_type.reset_policy if balance_type else "never"
            last = bal.last_reset_at
            try:
                if policy == "daily":
                    if not last or last.date() < now.date():
                        bal._do_reset(reason="daily")
                elif policy == "periodic":
                    days = balance_type.reset_period_days or 0
                    if days and (not last or (now - last).days >= days):
                        bal._do_reset(reason="periodic")
                # 'never' / 'manual' → skip (structural allocations preserved)
            except Exception:  # pragma: no cover - isolate per-record failures
                _logger.exception("Balance reset failed for balance %s", bal.id)
        return True


class AlkCommissionRule(models.Model):
    """Multi-tier commission rule (Mifos X-inspired).

    Drives the automatic commission lines posted to the ledger. Tiers and rates are
    fully GUI-configurable; nothing about the commission structure is hardcoded.
    """

    _name = "alkathiry.commission.rule"
    _description = "Alkathiry Commission Rule"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    service_id = fields.Many2one("alkathiry.service", string="Service", index=True)
    tier = fields.Integer(string="Commission Tier", default=1)
    rate_type = fields.Selection(
        selection=[("percent", "Percentage"), ("fixed", "Fixed Amount")],
        default="percent",
        required=True,
    )
    rate_value = fields.Float(string="Rate / Amount", default=0.0)
    # JSON predicate deciding when this commission applies.
    condition_expression = fields.Json(string="Condition")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
