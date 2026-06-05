from odoo import fields, models


class AlkTransaction(models.Model):
    """Immutable double-entry ledger record (Mifos X-inspired financial core).

    Every monetary movement, quota consumption, commission and withdrawal is an
    insert-only row here. Immutability is enforced at the database layer by a
    ``BEFORE UPDATE OR DELETE`` trigger (installed in ``init``) so no application
    path — ORM, SQL, or otherwise — can alter or remove a posted transaction.

    Double-entry is modelled by pairing rows through ``move_uid``: a single logical
    move groups its debit and credit legs under the same UID.
    """

    _name = "alkathiry.transaction"
    _description = "Alkathiry Immutable Transaction Ledger"
    _order = "id desc"

    # Human-friendly immutable reference (PRD: transaction_number).
    transaction_number = fields.Char(
        string="Transaction Number",
        required=True,
        copy=False,
        index=True,
    )

    # --- Move grouping (double-entry) ---
    move_uid = fields.Char(
        string="Move UID",
        required=True,
        index=True,
        help="Groups the debit and credit legs of one logical accounting move.",
    )
    direction = fields.Selection(
        selection=[("debit", "Debit"), ("credit", "Credit")],
        string="Direction",
        required=True,
    )

    # --- Parties & balance affected ---
    wallet_id = fields.Many2one("alkathiry.wallet", string="Wallet", index=True)
    balance_type_id = fields.Many2one(
        "alkathiry.balance.type.config",
        string="Balance Type",
        index=True,
    )
    partner_id = fields.Many2one("res.partner", string="Beneficiary", index=True)
    distributor_id = fields.Many2one("alkathiry.distributor", string="Distributor", index=True)

    # --- Source of the movement (polymorphic) ---
    transaction_type = fields.Selection(
        selection=[
            ("redemption", "Service Redemption"),
            ("topup", "Top-up / Allocation"),
            ("commission", "Commission"),
            ("withdrawal", "Withdrawal"),
            ("adjustment", "Adjustment"),
            ("revenue", "Revenue"),
            ("expense", "Expense"),
        ],
        string="Type",
        required=True,
        index=True,
    )
    service_id = fields.Many2one("alkathiry.service", string="Service", index=True)
    service_allocation_id = fields.Many2one(
        "alkathiry.service.allocation", string="Service Allocation", index=True
    )
    # Classifies revenue/expense lines for the income statement (§23.5.3).
    revenue_stream = fields.Selection(
        selection=[
            ("commission", "Commission"),
            ("advertisement", "Advertisement"),
            ("subscription", "Subscription"),
            ("donation", "Donation"),
            ("other", "Other"),
        ],
        string="Revenue Stream",
        index=True,
    )
    # Generic reference to any originating document (claim, withdrawal request, ...).
    source_ref = fields.Reference(
        selection=[
            ("alkathiry.service.allocation", "Service Allocation"),
            ("alkathiry.identity.token", "Identity Token"),
            ("alkathiry.commission.rule", "Commission Rule"),
        ],
        string="Source Document",
    )

    amount = fields.Float(string="Amount", required=True)
    quantity = fields.Float(string="Quantity", help="For in-kind / voucher movements.")
    currency_id = fields.Many2one("res.currency", string="Currency")

    # --- Redemption-loop linkage (Sequence Diagram 26.1) ---
    barcode_session_id = fields.Char(string="Barcode Session", index=True)
    otp_hash = fields.Char(string="OTP Hash")
    delegation_id = fields.Many2one("alkathiry.delegation", string="Via Delegation")
    delegated_for_partner_id = fields.Many2one(
        "res.partner",
        string="Delegated For",
        help="Originating beneficiary when redemption is performed by a proxy.",
        index=True,
    )

    # --- Multi-tier commission split (PRD 24.2.5) ---
    commission_distributor = fields.Float(string="Distributor Commission")
    commission_committee = fields.Float(string="Committee Commission")

    status = fields.Selection(
        selection=[("success", "Success"), ("failed", "Failed")],
        string="Result",
        default="success",
        required=True,
        index=True,
    )
    failure_reason = fields.Char(string="Failure Reason")

    # --- Immutability / audit columns ---
    posted_at = fields.Datetime(string="Posted At", default=fields.Datetime.now, required=True)
    posted_by = fields.Many2one("res.users", string="Posted By", default=lambda self: self.env.user)
    # Hash chain anchor: hash of (previous row hash + this row payload).
    prev_hash = fields.Char(string="Previous Hash", index=True)
    row_hash = fields.Char(string="Row Hash", index=True)
    notes = fields.Text()

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "transaction_number_uniq",
            "unique(transaction_number)",
            "Transaction number must be globally unique.",
        ),
    ]

    def init(self):
        super().init()
        # Composite index for per-beneficiary / per-window quota lookups.
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS
                alkathiry_transaction_quota_lookup_idx
            ON alkathiry_transaction
                (partner_id, service_allocation_id, transaction_type, posted_at)
            """
        )
        # --- Absolute immutability: block UPDATE and DELETE at the DB level ---
        # PostgreSQL 15+ supports CREATE OR REPLACE TRIGGER, so re-running module
        # upgrades is idempotent.
        self.env.cr.execute(
            """
            CREATE OR REPLACE FUNCTION alkathiry_transaction_block_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION
                    'alkathiry.transaction rows are immutable: % is not permitted',
                    TG_OP
                    USING ERRCODE = 'check_violation';
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        self.env.cr.execute(
            """
            CREATE OR REPLACE TRIGGER alkathiry_transaction_immutable
            BEFORE UPDATE OR DELETE ON alkathiry_transaction
            FOR EACH ROW EXECUTE FUNCTION alkathiry_transaction_block_mutation();
            """
        )
