from odoo import fields, models


class AlkService(models.Model):
    """A distributable service / programme (OpenSPP service engine inspired).

    Carries a JSON-defined targeting expression that the polymorphic validation
    engine (Step 3) evaluates against beneficiary attributes, region and category
    membership, and age rules.
    """

    _name = "alkathiry.service"
    _description = "Alkathiry Service"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string="Technical Code", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)

    distribution_model = fields.Selection(
        selection=[
            ("a", "Model A"),
            ("b", "Model B"),
            ("c", "Model C"),
        ],
        string="Distribution Model",
        default="a",
        required=True,
        help="Declares which fulfillment UI the Distributor Flutter app renders "
        "for this service (Step 4).",
    )

    balance_type_id = fields.Many2one(
        "alkathiry.balance.type.config",
        string="Charged Balance Type",
        required=True,
        help="Wallet balance type debited / consumed when this service is redeemed.",
    )

    # JSON-defined targeting predicate (regions, categories, age rules, ...).
    targeting_expression = fields.Json(
        string="Targeting Expression",
        help="Dynamic conditional predicate evaluated to decide beneficiary "
        "eligibility. No targeting logic is hardcoded.",
    )
    category_ids = fields.Many2many(
        "alkathiry.dynamic.category",
        string="Targeted Categories",
        help="Convenience pre-filter; the full predicate lives in "
        "targeting_expression.",
    )

    allocation_ids = fields.One2many(
        "alkathiry.service.allocation",
        "service_id",
        string="Allocations",
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The service code must be unique per company.",
        ),
    ]


class AlkServiceAllocation(models.Model):
    """A scheduled distribution of quota for a service over a timeline.

    Holds the per-cycle quota and the active window. The validation engine checks
    that an allocation is current on the timeline (FR-DIS-03 #3) and that the
    beneficiary has unspent quota within the current reset window (#4).
    """

    _name = "alkathiry.service.allocation"
    _description = "Alkathiry Service Allocation"
    _order = "date_start desc, id desc"

    name = fields.Char(required=True, translate=True)
    service_id = fields.Many2one(
        "alkathiry.service",
        string="Service",
        required=True,
        ondelete="cascade",
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("active", "Active"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        index=True,
    )

    date_start = fields.Datetime(string="Start", required=True, index=True)
    date_end = fields.Datetime(string="End", index=True)

    # Targeting refinements applied on top of the service predicate.
    region_ids = fields.Many2many(
        "res.country.state",
        string="Targeted Regions",
        help="Regional filtering scope for this allocation.",
    )
    targeting_expression = fields.Json(
        string="Allocation Targeting Override",
        help="Optional override / refinement of the service-level predicate.",
    )

    # Quota per eligible beneficiary within one reset window.
    quota_per_beneficiary = fields.Float(
        string="Quota per Beneficiary",
        default=1.0,
        required=True,
    )
    total_quota = fields.Float(
        string="Total Quota",
        help="Optional global cap across all beneficiaries (0 = unlimited).",
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    def init(self):
        super().init()
        # Composite index supporting the "active & current on timeline" lookup
        # performed for every distribution claim (FR-DIS-03 #3).
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS
                alkathiry_service_allocation_state_window_idx
            ON alkathiry_service_allocation (state, date_start, date_end)
            """
        )
