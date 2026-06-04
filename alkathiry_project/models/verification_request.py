import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AlkVerificationRequest(models.Model):
    """A registration/verification record traversing the dynamic pipeline.

    Step 2 — Metadata-Driven Hierarchical Verification Engine.

    The state machine advances by reading the active sequence from
    ``alkathiry.verification.stage.config`` (or a category override) rather than a
    hardcoded enum. It enforces BR-VER-03 (auto-escalation after X consecutive
    rejections), resolves authorised verifiers per scope (FR-VER-05) and is swept
    by an SLA cron for reminders and timeout escalation.
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

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") in (False, "New"):
                seq = self.env["ir.sequence"].next_by_code("alkathiry.verification.request")
                vals["name"] = seq or "New"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Dynamic pipeline resolution
    # ------------------------------------------------------------------
    def _get_pipeline_stages(self):
        """Return the ordered stage recordset for this request.

        Uses the category's pipeline override when configured, otherwise the
        company-wide active pipeline. No order is hardcoded.
        """
        self.ensure_one()
        Stage = self.env["alkathiry.verification.stage.config"]
        if self.category_id and self.category_id.stage_config_ids:
            return self.category_id.stage_config_ids.filtered("active").sorted(
                lambda s: (s.sequence, s.id)
            )
        return Stage.search(
            [("active", "=", True), ("company_id", "=", self.company_id.id)],
            order="sequence, id",
        )

    def _committee_stage(self):
        """Resolve the terminal committee tier (or the last tier as fallback)."""
        self.ensure_one()
        stages = self._get_pipeline_stages()
        committee = stages.filtered("is_committee")
        return committee[:1] or stages[-1:]

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            stages = rec._get_pipeline_stages()
            if not stages:
                raise UserError(_("No active verification stages are configured."))
            rec.write(
                {
                    "state": "in_progress",
                    "current_stage_id": stages[0].id,
                    "consecutive_rejections": 0,
                }
            )
            rec._enter_stage(stages[0])
            if rec.partner_id.alk_status in ("draft", False):
                rec.partner_id.alk_status = "under_verification"
            rec._log_audit("submit", {"stage": stages[0].code})
        return True

    def action_approve(self, remarks=None):
        """Approve the current tier; advance or finalize per the dynamic pipeline."""
        self.ensure_one()
        self._ensure_actionable()
        stage = self.current_stage_id
        self._check_verifier_allowed(self.env.user, stage)
        self._record_decision(stage, "approved", remarks)

        # Quorum policy: wait until enough approvals are gathered at this tier.
        if stage.approval_policy == "quorum":
            approvals = self.line_ids.filtered(
                lambda line, s=stage: line.stage_id == s and line.decision == "approved"
            )
            if len(approvals) < max(stage.required_approvals, 1):
                self._log_audit("approve_partial", {"stage": stage.code})
                return True

        # An approval resets the consecutive-rejection counter (BR-VER-03).
        self.consecutive_rejections = 0
        stages = self._get_pipeline_stages()
        ids = stages.ids
        is_last = stage.id not in ids or ids.index(stage.id) == len(ids) - 1
        if self.state == "escalated" or stage.is_committee or is_last:
            self._finalize_approved()
        else:
            self._enter_stage(stages[ids.index(stage.id) + 1])
        self._log_audit("approve", {"stage": stage.code})
        return True

    def action_reject(self, remarks=None):
        """Reject at the current tier; escalate to committee after X in a row."""
        self.ensure_one()
        self._ensure_actionable()
        stage = self.current_stage_id
        self._check_verifier_allowed(self.env.user, stage)
        self._record_decision(stage, "rejected", remarks)

        # A rejection at the committee tier (or while escalated) is terminal.
        if stage.is_committee or self.state == "escalated":
            self._finalize_rejected()
            self._log_audit("reject_final", {"stage": stage.code})
            return True

        self.consecutive_rejections += 1
        max_rej = self.company_id.alk_max_consecutive_rejections or 0
        self._log_audit("reject", {"stage": stage.code, "count": self.consecutive_rejections})
        if max_rej and self.consecutive_rejections >= max_rej:
            self.action_escalate_to_committee(reason="consecutive_rejections")
        return True

    def action_escalate_to_committee(self, reason=None):
        """Jump the request directly to the committee tier (BR-VER-03 / SLA)."""
        self.ensure_one()
        committee = self._committee_stage()
        if not committee:
            raise UserError(_("No committee (terminal) stage is configured."))
        if self.current_stage_id:
            self._record_decision(
                self.current_stage_id, "escalated", _("Escalated (%s)") % (reason or "manual")
            )
        self.state = "escalated"
        self._enter_stage(committee)
        self.message_post(body=_("Escalated to the Central Committee (reason: %s).") % (reason or "manual"))
        self._log_audit("escalate", {"reason": reason, "committee": committee.code})
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _enter_stage(self, stage):
        self.ensure_one()
        self.write(
            {
                "current_stage_id": stage.id,
                "stage_entered_at": fields.Datetime.now(),
                "reminder_sent_at": False,
            }
        )

    def _record_decision(self, stage, decision, remarks):
        self.ensure_one()
        return self.env["alkathiry.verification.request.line"].create(
            {
                "request_id": self.id,
                "stage_id": stage.id,
                "sequence": stage.sequence,
                "verifier_id": self.env.user.id,
                "decision": decision,
                "decision_date": fields.Datetime.now(),
                "remarks": remarks,
            }
        )

    def _finalize_approved(self):
        self.ensure_one()
        self.state = "approved"
        self.partner_id.write(
            {"alk_status": "active", "alk_activated_at": fields.Datetime.now()}
        )
        self.message_post(body=_("Verification approved — beneficiary activated."))

    def _finalize_rejected(self):
        self.ensure_one()
        self.state = "rejected"
        self.partner_id.alk_status = "rejected"
        self.message_post(body=_("Verification rejected."))

    def _ensure_actionable(self):
        self.ensure_one()
        if self.state not in ("in_progress", "escalated"):
            raise UserError(_("This request is not awaiting a decision."))
        if not self.current_stage_id:
            raise UserError(_("No current verification tier is set."))

    # --- FR-VER-05: multi-role / multi-scope verifier matching ---
    def _match_verifiers(self, stage=None):
        """Return res.users authorised to act on the given tier for this applicant.

        A verifier matches when assigned to the tier and either the tier is global
        (committee), the assignment has no area scope, or the applicant's area is
        the assignment's area or any descendant of it (dynamic tree containment).
        """
        self.ensure_one()
        stage = stage or self.current_stage_id
        if not stage:
            return self.env["res.users"]
        assignments = self.env["alkathiry.verifier.role.assignment"].search(
            [("stage_id", "=", stage.id), ("active", "=", True)]
        )
        partner_area = self.partner_id.alk_area_id

        def _in_scope(assignment):
            if stage.is_committee or stage.scope_type == "global":
                return True
            if not assignment.area_id:
                return True
            if partner_area and partner_area.parent_path and assignment.area_id.parent_path:
                return partner_area.parent_path.startswith(assignment.area_id.parent_path)
            return False

        return assignments.filtered(_in_scope).mapped("user_id")

    def _check_verifier_allowed(self, user, stage):
        if user.has_group("base.group_system"):
            return True
        if user not in self._match_verifiers(stage):
            raise UserError(
                _("You are not an authorised verifier for the current tier and scope.")
            )
        return True

    def _log_audit(self, action, metadata=None):
        self.ensure_one()
        self.env["alkathiry.audit.log"].sudo().create(
            {
                "action": f"verification.{action}",
                "actor_role": self.current_stage_id.code if self.current_stage_id else False,
                "model_name": self._name,
                "res_id": self.id,
                "user_id": self.env.user.id,
                "metadata": metadata or {},
            }
        )

    # ------------------------------------------------------------------
    # SLA engine (cron): reminders at T, auto-escalation at T+escalation
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_sla(self):
        now = fields.Datetime.now()
        pending = self.search(
            [
                ("state", "in", ["in_progress", "escalated"]),
                ("stage_entered_at", "!=", False),
            ]
        )
        for rec in pending:
            stage = rec.current_stage_id
            if not stage:
                continue
            company = rec.company_id
            esc_hours = stage.sla_escalation_hours or company.alk_sla_escalation_hours or 0.0
            rem_hours = stage.sla_reminder_hours or company.alk_sla_reminder_hours or 0.0
            elapsed = (now - rec.stage_entered_at).total_seconds() / 3600.0
            try:
                if (
                    rec.state != "escalated"
                    and not stage.is_committee
                    and esc_hours
                    and elapsed >= esc_hours
                ):
                    rec.action_escalate_to_committee(reason="sla_timeout")
                elif rem_hours and elapsed >= rem_hours and not rec.reminder_sent_at:
                    rec._send_sla_reminder()
            except Exception:  # pragma: no cover - never let one record break the sweep
                _logger.exception("SLA sweep failed for verification request %s", rec.id)
        return True

    def _send_sla_reminder(self):
        self.ensure_one()
        verifiers = self._match_verifiers()
        body = _(
            "Reminder: verification request %(ref)s is awaiting a decision at tier "
            "'%(tier)s'."
        ) % {"ref": self.name, "tier": self.current_stage_id.display_name}
        self.message_post(body=body, partner_ids=verifiers.mapped("partner_id").ids)
        self.reminder_sent_at = fields.Datetime.now()


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
