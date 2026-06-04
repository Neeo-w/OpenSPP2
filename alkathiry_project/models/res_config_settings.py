from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Exposes the Alkathiry global timing & governance parameters in Settings.

    These mirror the ``res.company`` fields so the Central Committee tunes the
    verification, redemption and reset behaviour entirely from the Admin UI.
    """

    _inherit = "res.config.settings"

    alk_max_consecutive_rejections = fields.Integer(
        related="company_id.alk_max_consecutive_rejections", readonly=False
    )
    alk_sla_reminder_hours = fields.Float(
        related="company_id.alk_sla_reminder_hours", readonly=False
    )
    alk_sla_escalation_hours = fields.Float(
        related="company_id.alk_sla_escalation_hours", readonly=False
    )
    alk_barcode_token_ttl_seconds = fields.Integer(
        related="company_id.alk_barcode_token_ttl_seconds", readonly=False
    )
    alk_otp_ttl_seconds = fields.Integer(
        related="company_id.alk_otp_ttl_seconds", readonly=False
    )
    alk_daily_reset_time = fields.Char(
        related="company_id.alk_daily_reset_time", readonly=False
    )
