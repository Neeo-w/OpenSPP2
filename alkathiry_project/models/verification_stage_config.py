from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AlkVerificationStageConfig(models.Model):
    """Dynamic, re-orderable verification levels (MOSIP-inspired).

    Replaces any hardcoded ``pending_aqil`` / ``pending_sheikh`` pipeline enum.
    The admin can add, remove, re-order or rename levels to move from the default
    4-stage Aqil → Sheikh → Grand Sheikh → Committee workflow to any arbitrary
    N-tier workflow without code changes. The verification state machine (Step 2)
    pulls its sequence directly from active records of this model.
    """

    _name = "alkathiry.verification.stage.config"
    _description = "Alkathiry Verification Stage Configuration"
    _order = "sequence, id"

    name = fields.Char(
        string="Stage Name",
        required=True,
        translate=True,
        help="Human-readable name of the tier, e.g. Aqil, Sheikh, Grand Sheikh, "
        "Central Committee.",
    )
    code = fields.Char(
        string="Technical Code",
        required=True,
        help="Stable identifier used by the engine and API payloads. Renaming the "
        "display name does not change the code.",
    )
    sequence = fields.Integer(
        string="Order",
        default=10,
        index=True,
        help="Position of this tier in the verification pipeline. Lower runs first.",
    )
    active = fields.Boolean(default=True)

    # --- Role / scope binding ---
    role_id = fields.Many2one(
        "res.groups",
        string="Authorised Role",
        help="Security group whose members may act on requests at this tier.",
    )
    scope_type = fields.Selection(
        selection=[
            ("neighborhood", "Neighborhood"),
            ("tribe", "Tribe"),
            ("region", "Region"),
            ("global", "Global / Committee"),
        ],
        string="Geographic Scope",
        default="neighborhood",
        required=True,
        help="Geographic granularity at which a verifier of this tier is matched "
        "to a request (supports multi-role mapping, FR-VER-05).",
    )
    is_committee = fields.Boolean(
        string="Is Central Committee Tier",
        default=False,
        help="Marks the terminal governance tier that receives auto-escalations.",
    )

    # --- SLA timing (overrides company defaults when set) ---
    sla_reminder_hours = fields.Float(
        string="SLA Reminder Override (hours)",
        help="Optional per-stage override of the company reminder threshold.",
    )
    sla_escalation_hours = fields.Float(
        string="SLA Escalation Override (hours)",
        help="Optional per-stage override of the company escalation threshold.",
    )

    # --- Decision policy ---
    approval_policy = fields.Selection(
        selection=[
            ("single", "Single Approver"),
            ("any", "Any Authorised Verifier"),
            ("quorum", "Quorum / Multiple Approvers"),
        ],
        string="Approval Policy",
        default="single",
        required=True,
    )
    required_approvals = fields.Integer(
        string="Required Approvals",
        default=1,
        help="Number of approvals needed when the policy is 'quorum'.",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The verification stage code must be unique per company.",
        ),
    ]

    @api.constrains("approval_policy", "required_approvals")
    def _check_required_approvals(self):
        for rec in self:
            if rec.approval_policy == "quorum" and rec.required_approvals < 2:
                raise ValidationError(_("A quorum policy requires at least 2 approvals."))
