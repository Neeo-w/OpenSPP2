from odoo import fields, models


class ResCompany(models.Model):
    """Global, GUI-configurable system timing & governance parameters.

    Per the "Absolute Dynamism" mandate, every threshold that drives a workflow
    is stored here (or on the relevant config model) so the Central Committee can
    tune behaviour from the Odoo Admin UI without touching backend or mobile code.
    """

    _inherit = "res.company"

    # --- Hierarchical verification governance (BR-VER-03) ---
    alk_max_consecutive_rejections = fields.Integer(
        string="Max Consecutive Rejections Before Committee Escalation",
        default=2,
        help="X in BR-VER-03. When a verification request accumulates this many "
        "consecutive rejections at any dynamic tier, it is auto-escalated "
        "directly to the Central Committee.",
    )

    # --- Verifier SLA alerts (configurable T) ---
    alk_sla_reminder_hours = fields.Float(
        string="SLA Reminder (hours)",
        default=12.0,
        help="T: a reminder is sent to the assigned verifier after this many hours "
        "of inactivity on a pending verification line.",
    )
    alk_sla_escalation_hours = fields.Float(
        string="SLA Auto-Escalation (hours)",
        default=24.0,
        help="T+24 by default: after this many hours the pending line is "
        "auto-escalated to the Central Committee.",
    )

    # --- Distribution transaction loop (Sequence Diagram 26.1) ---
    alk_barcode_token_ttl_seconds = fields.Integer(
        string="Beneficiary Barcode/JWT TTL (seconds)",
        default=300,
        help="Lifetime of the encrypted JWT embedded in the beneficiary's dynamic "
        "barcode. Default 5 minutes.",
    )
    alk_otp_ttl_seconds = fields.Integer(
        string="Redemption OTP TTL (seconds)",
        default=120,
        help="Lifetime of the OTP issued to the beneficiary device during a "
        "distributor scan. Default 2 minutes.",
    )

    # --- Nightly reset engine ---
    alk_daily_reset_time = fields.Char(
        string="Daily Balance Reset Time",
        default="23:59:59",
        help="Local time at which the nightly engine zeroes out balances whose "
        "balance type is configured to reset daily.",
    )
