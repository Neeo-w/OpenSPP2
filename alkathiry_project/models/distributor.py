from odoo import api, fields, models


class AlkDistributor(models.Model):
    """A field distributor operating the Distributor Flutter app.

    Holds the per-distributor on-hand allocations that the validation engine checks
    against FR-DIS-03 #5 (sufficient remaining quantities on hand).
    """

    _name = "alkathiry.distributor"
    _description = "Alkathiry Distributor"
    _order = "name"

    name = fields.Char(required=True)
    user_id = fields.Many2one("res.users", string="Linked User", index=True)
    partner_id = fields.Many2one("res.partner", string="Contact", index=True)
    active = fields.Boolean(default=True)

    region_id = fields.Many2one("res.country.state", string="Operating Region", index=True)
    allocation_ids = fields.One2many(
        "alkathiry.distributor.allocation",
        "distributor_id",
        string="On-hand Allocations",
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )


class AlkDistributorAllocation(models.Model):
    """Quantities handed to a distributor for a specific service allocation."""

    _name = "alkathiry.distributor.allocation"
    _description = "Alkathiry Distributor Allocation"
    _order = "distributor_id, service_allocation_id"

    distributor_id = fields.Many2one(
        "alkathiry.distributor",
        string="Distributor",
        required=True,
        ondelete="cascade",
        index=True,
    )
    service_allocation_id = fields.Many2one(
        "alkathiry.service.allocation",
        string="Service Allocation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    quantity_assigned = fields.Float(string="Assigned Quantity", default=0.0)
    quantity_distributed = fields.Float(string="Distributed Quantity", default=0.0)
    quantity_on_hand = fields.Float(
        string="Quantity On Hand",
        compute="_compute_quantity_on_hand",
        store=True,
    )
    commission_rate = fields.Float(
        string="Commission Rate (%)",
        help="Distributor commission for this allocation (PRD 24.2.4).",
    )
    shipment_status = fields.Selection(
        selection=[
            ("pending_shipment", "Pending Shipment"),
            ("shipped", "Shipped"),
            ("received_confirmed", "Received - Confirmed"),
            ("received_with_issue", "Received - With Issue"),
        ],
        string="Shipment Status",
        default="pending_shipment",
        index=True,
    )
    confirmed_at = fields.Datetime(string="Confirmed At")
    issue_note = fields.Text(string="Issue Note")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    @api.depends("quantity_assigned", "quantity_distributed")
    def _compute_quantity_on_hand(self):
        for rec in self:
            rec.quantity_on_hand = rec.quantity_assigned - rec.quantity_distributed

    _sql_constraints = [
        (
            "distributor_alloc_uniq",
            "unique(distributor_id, service_allocation_id)",
            "A distributor has a single on-hand line per service allocation.",
        ),
    ]
