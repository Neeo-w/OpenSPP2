from odoo import fields, models


class AlkVerificationRequest(models.Model):
    """A registration/verification record traversing the dynamic pipeline.

    The state machine engine (Step 2 — to be implemented after sign-off) advances
    the record by reading the active sequence from
    ``alkathiry.verification.stage.config`` rather than a hardcoded enum. This model
    is the data backbone for that engine: it tracks the current tier, the per-tier
    decisions, and the consecutive-rejection counter that drives committee
    escalation (BR-VER-03).
    """

    _name = "alkathiry.verification.request"
    _description = "Alkathiry Verification Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Reference", required=True, copy=False, default="New", index=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Applicant",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    category_id = fields.Many2one(
        "alkathiry.dynamic.category",
        string="Requested Category",
        required=True,
        index=True,
    )

    # The pipeline is resolved dynamically; current_stage_id points into the config.
    current_stage_id = fields.Many2one(
        "alkathiry.verification.stage.config",
        string="Current Tier",
        index=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("escalated", "Escalated to Committee"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )

    consecutive_rejections = fields.Integer(
        string="Consecutive Rejections",
        default=0,
        help="Counter compared against the company's max-rejections parameter to "
        "trigger automatic escalation (BR-VER-03).",
    )

    # Snapshot of the submitted dynamic field values at request time.
    submitted_values = fields.Json(string="Submitted Values")

    line_ids = fields.One2many(
        "alkathiry.verification.request.line",
        "request_id",
        string="Tier Decisions",
    )

    # SLA bookkeeping for the current pending tier (driven by configurable timing).
    stage_entered_at = fields.Datetime(string="Current Tier Entered At")
    reminder_sent_at = fields.Datetime(string="Reminder Sent At")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )


class AlkVerificationRequestLine(models.Model):
    """One decision taken at one dynamic tier of a verification request."""

    _name = "alkathiry.verification.request.line"
    _description = "Alkathiry Verification Request Line"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        "alkathiry.verification.request",
        string="Request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    stage_id = fields.Many2one(
        "alkathiry.verification.stage.config",
        string="Tier",
        required=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    verifier_id = fields.Many2one("res.users", string="Decided By", index=True)
    decision = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("escalated", "Escalated"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    decision_date = fields.Datetime(string="Decision Date")
    remarks = fields.Text()
