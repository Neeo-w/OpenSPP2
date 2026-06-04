from odoo import fields, models


class AlkServiceProvider(models.Model):
    """Service provider (PRD 24.2.4 ``service_providers``).

    Charities, commercial vendors, government bodies or individuals who fund or
    supply services. A provider may also act as a distributor
    (``is_distributor_too``). Contract terms and fee structures are stored as JSON
    so they remain fully configurable.
    """

    _name = "alkathiry.service.provider"
    _description = "Alkathiry Service Provider"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    provider_type = fields.Selection(
        selection=[
            ("charity", "Charity"),
            ("commercial", "Commercial"),
            ("government", "Government"),
            ("individual", "Individual"),
        ],
        string="Type",
        required=True,
        default="charity",
        index=True,
    )
    partner_id = fields.Many2one("res.partner", string="Linked Contact", index=True)
    contact_phone = fields.Char()
    contact_email = fields.Char()

    # Fully configurable contractual / fee structure.
    contract_terms = fields.Json(string="Contract Terms")
    service_fee_rate = fields.Float(
        string="Committee Fee Rate (%)",
        help="Commission percentage retained by the committee on this provider's "
        "services.",
    )
    is_distributor_too = fields.Boolean(string="Also a Distributor", default=False)
    distributor_id = fields.Many2one(
        "alkathiry.distributor",
        string="Distributor Profile",
        help="Set when this provider also distributes (is_distributor_too).",
    )

    status = fields.Selection(
        selection=[
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("terminated", "Terminated"),
        ],
        default="active",
        required=True,
        index=True,
    )
    service_ids = fields.One2many("alkathiry.service", "provider_id", string="Services")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
