from odoo import fields, models


class AlkVerifierRoleAssignment(models.Model):
    """Multi-role, multi-scope verifier mapping (FR-VER-05).

    A single account can hold several structural verifier roles, each bound to a
    distinct geographic scope — e.g. acting as an Aqil for Neighborhood A and a
    Sheikh for Tribe B simultaneously. The verification engine matches a pending
    request to verifiers by (stage, scope_type, scope_value).
    """

    _name = "alkathiry.verifier.role.assignment"
    _description = "Alkathiry Verifier Role Assignment"
    _order = "user_id, stage_id"

    user_id = fields.Many2one(
        "res.users",
        string="Verifier",
        required=True,
        ondelete="cascade",
        index=True,
    )
    stage_id = fields.Many2one(
        "alkathiry.verification.stage.config",
        string="Verification Tier",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # Concrete geographic scope this assignment is limited to. The interpretation
    # of scope_value depends on the stage's scope_type.
    scope_type = fields.Selection(
        related="stage_id.scope_type",
        string="Scope Type",
        store=True,
        index=True,
    )
    scope_value = fields.Char(
        string="Scope Value",
        help="Concrete scope, e.g. neighborhood or tribe name, or a region key. "
        "Empty means the assignment applies to the whole scope type.",
        index=True,
    )
    region_id = fields.Many2one("res.country.state", string="Region Scope", index=True)

    active = fields.Boolean(default=True)
    date_start = fields.Date(string="Valid From")
    date_end = fields.Date(string="Valid Until")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "user_stage_scope_uniq",
            "unique(user_id, stage_id, scope_value, region_id)",
            "This verifier already holds this tier for the given scope.",
        ),
    ]

    def init(self):
        super().init()
        # Composite index for the engine's verifier-matching query.
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS
                alkathiry_verifier_role_match_idx
            ON alkathiry_verifier_role_assignment
                (stage_id, scope_type, scope_value, region_id)
            """
        )
