from odoo import fields, models


class AlkAuditLog(models.Model):
    """Immutable, append-only audit log.

    Records every security-relevant action across the platform (verification
    decisions, token issuance, distribution confirmations, configuration changes).
    Like the transaction ledger, it is protected by a ``BEFORE UPDATE OR DELETE``
    database trigger so entries can never be altered or erased.
    """

    _name = "alkathiry.audit.log"
    _description = "Alkathiry Immutable Audit Log"
    _order = "id desc"

    event_time = fields.Datetime(string="Event Time", default=fields.Datetime.now, required=True)
    user_id = fields.Many2one("res.users", string="Actor", default=lambda self: self.env.user)
    action = fields.Char(string="Action", required=True, index=True)
    model_name = fields.Char(string="Model", index=True)
    res_id = fields.Integer(string="Record ID", index=True)

    # Polymorphic before/after snapshots.
    old_values = fields.Json(string="Old Values")
    new_values = fields.Json(string="New Values")
    metadata = fields.Json(string="Context Metadata")

    # Hash chain for tamper evidence.
    prev_hash = fields.Char(string="Previous Hash", index=True)
    row_hash = fields.Char(string="Row Hash", index=True)

    ip_address = fields.Char(string="Source IP")
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    def init(self):
        super().init()
        self.env.cr.execute(
            """
            CREATE OR REPLACE FUNCTION alkathiry_audit_log_block_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION
                    'alkathiry.audit.log rows are immutable: % is not permitted',
                    TG_OP
                    USING ERRCODE = 'check_violation';
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        self.env.cr.execute(
            """
            CREATE OR REPLACE TRIGGER alkathiry_audit_log_immutable
            BEFORE UPDATE OR DELETE ON alkathiry_audit_log
            FOR EACH ROW EXECUTE FUNCTION alkathiry_audit_log_block_mutation();
            """
        )
