from odoo import fields, models


class AlkDynamicCategory(models.Model):
    """Admin-defined user categories / demographics (OpenSPP target-group inspired).

    The Central Committee creates categories from the dashboard and declares, per
    category, the required verification method and the dynamic set of registration
    fields. The Beneficiary Flutter app renders its step-by-step registration form
    purely from this metadata (Step 4).
    """

    _name = "alkathiry.dynamic.category"
    _description = "Alkathiry Dynamic User Category"
    _order = "sequence, name"

    name = fields.Char(string="Category Name", required=True, translate=True)
    code = fields.Char(string="Technical Code", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)

    verification_method = fields.Selection(
        selection=[
            ("self_declaration", "Self-declaration"),
            ("documentary", "Documentary Evidence"),
            ("committee", "Committee Approval"),
        ],
        string="Required Verification Method",
        default="self_declaration",
        required=True,
        help="Governs how membership of this category is substantiated during "
        "registration and verification.",
    )

    # Optional override of the global pipeline for members of this category.
    stage_config_ids = fields.Many2many(
        "alkathiry.verification.stage.config",
        string="Verification Pipeline Override",
        help="If set, members of this category follow exactly these tiers (in their "
        "configured order) instead of the global active pipeline.",
    )

    field_ids = fields.One2many(
        "alkathiry.category.field",
        "category_id",
        string="Dynamic Registration Fields",
    )

    # JSON-defined eligibility predicate evaluated by the validation engine (Step 3).
    eligibility_domain = fields.Json(
        string="Eligibility Predicate",
        help="Dynamic targeting expression (regions / categories / age rules) used "
        "to decide whether a beneficiary satisfies this category at claim time.",
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
            "The category code must be unique per company.",
        ),
    ]


class AlkCategoryField(models.Model):
    """Metadata description of a single dynamic registration input.

    These rows are serialised into the JSON payload the Flutter app uses to build
    its registration UI reflectively (input fields, checkboxes, dropdowns, document
    upload slots) without any compiled-in layout.
    """

    _name = "alkathiry.category.field"
    _description = "Alkathiry Category Dynamic Field"
    _order = "category_id, sequence, id"

    category_id = fields.Many2one(
        "alkathiry.dynamic.category",
        string="Category",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Field Label", required=True, translate=True)
    technical_name = fields.Char(
        string="Field Key",
        required=True,
        help="Key emitted in the JSON payload and expected back in the submission.",
    )
    field_type = fields.Selection(
        selection=[
            ("char", "Text"),
            ("text", "Long Text"),
            ("integer", "Integer"),
            ("float", "Decimal"),
            ("boolean", "Checkbox"),
            ("date", "Date"),
            ("selection", "Dropdown"),
            ("multiselect", "Multi-select"),
            ("document", "Document Upload"),
            ("image", "Image / Photo"),
        ],
        string="Field Type",
        required=True,
        default="char",
    )
    required = fields.Boolean(default=False)
    # For selection / multiselect types: list of {"value": ..., "label": ...}.
    selection_options = fields.Json(string="Options")
    # Optional client-side validation hints (regex, min, max, accepted mimetypes).
    validation_rules = fields.Json(string="Validation Rules")
    placeholder = fields.Char(translate=True)
    help_text = fields.Char(translate=True)

    _sql_constraints = [
        (
            "category_key_uniq",
            "unique(category_id, technical_name)",
            "Field keys must be unique within a category.",
        ),
    ]
