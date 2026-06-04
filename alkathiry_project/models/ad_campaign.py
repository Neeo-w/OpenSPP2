from odoo import fields, models


class AlkAdCampaign(models.Model):
    """Hyper-targeted advertisement campaign served to mobile apps.

    Operates independently of service execution: serving banners never touches the
    primary distribution flow. Targeting reuses the same JSON predicate style as
    services so the same dynamic evaluator can be applied.
    """

    _name = "alkathiry.ad.campaign"
    _description = "Alkathiry Advertisement Campaign"
    _order = "sequence, date_start desc"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    provider_id = fields.Many2one(
        "alkathiry.service.provider",
        string="Provider",
        index=True,
        help="Advertiser funding the campaign (PRD 24.2).",
    )
    ad_type = fields.Selection(
        selection=[
            ("promotion", "Promotion"),
            ("clearance", "Clearance"),
            ("wholesale", "Wholesale"),
            ("rewards", "Rewards"),
        ],
        string="Ad Type",
        default="promotion",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("running", "Running"),
            ("paused", "Paused"),
            ("ended", "Ended"),
        ],
        default="draft",
        required=True,
        index=True,
    )

    date_start = fields.Datetime(string="Start", index=True)
    date_end = fields.Datetime(string="End", index=True)

    # Creative assets and the placement they target in the apps.
    banner_image = fields.Binary(string="Banner", attachment=True)
    media_url = fields.Char(string="Media URL")
    click_url = fields.Char(string="Click-through URL")
    placement = fields.Selection(
        selection=[
            ("beneficiary_home", "Beneficiary Home"),
            ("distributor_home", "Distributor Home"),
            ("verifier_home", "Verifier Home"),
        ],
        string="Placement",
        default="beneficiary_home",
        required=True,
    )

    # JSON targeting predicate (region / category / demographics).
    targeting_expression = fields.Json(string="Targeting Expression")
    priority = fields.Integer(string="Serving Priority", default=10)

    cost = fields.Float(string="Campaign Cost")
    commission_rate = fields.Float(string="Commission Rate (%)")
    impressions = fields.Integer(string="Impressions (Reach)", default=0)
    clicks = fields.Integer(string="Clicks", default=0)
    conversions = fields.Integer(string="Conversions", default=0)

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
