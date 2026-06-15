from odoo import api, fields, models


class ResPartner(models.Model):
    """Alkathiry community-profile extension on the registrant.

    No duplication: civil_status_id, occupation_id, income and address already
    exist in ``spp_registry`` and are reused. Lineage uses the clean
    ``alkathiry.tribe`` tree (not group membership); the responsible officials are
    resolved from the positions matrix by intersecting lineage node with area.
    """

    _inherit = "res.partner"

    # --- System identifier (no equivalent in spp; concept from OpenG2P unique_id) ---
    alk_citizen_no = fields.Char(
        string="Citizen No.",
        index=True,
        copy=False,
        readonly=True,
        help="System-generated unique community number for the individual.",
    )

    # --- Lineage link (clean parent/child/level tree, independent of geography) ---
    alk_tribe_node_id = fields.Many2one(
        "alkathiry.tribe",
        string="Lineage Node",
        index=True,
        help="The citizen's node in the tribal lineage tree (e.g. their family or "
        "fakheedah). Independent of where they currently live.",
    )
    alk_representative_ids = fields.Many2many(
        "res.users",
        string="Tribal Representatives",
        compute="_compute_alk_representatives",
        help="Officials resolved from the positions matrix by intersecting this "
        "individual's lineage node with their residential area.",
    )

    # --- Demographic / socio-economic dimensions (vocabulary-driven) ---
    alk_blood_type_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Blood Type",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:blood-type')]",
    )
    alk_health_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="General Health Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:health-status')]",
    )
    alk_education_level_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Education Level",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:education-level')]",
    )
    alk_employment_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Employment Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:employment-status')]",
    )
    alk_financial_status_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Financial Status",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:financial-status')]",
    )

    # --- Medical conditions / diseases (with proof attachments) ---
    alk_health_condition_ids = fields.One2many(
        "alkathiry.health.condition",
        "partner_id",
        string="Medical Conditions",
    )
    alk_health_condition_count = fields.Integer(
        compute="_compute_alk_health_condition_count",
    )

    @api.depends("alk_health_condition_ids")
    def _compute_alk_health_condition_count(self):
        for rec in self:
            rec.alk_health_condition_count = len(rec.alk_health_condition_ids)

    @api.depends("alk_tribe_node_id", "area_id")
    def _compute_alk_representatives(self):
        positions_model = self.env["alkathiry.tribe.position"]
        for rec in self:
            users = self.env["res.users"].browse()
            if rec.alk_tribe_node_id:
                # Positions whose lineage node is this node or an ancestor.
                positions = positions_model.search(
                    [
                        ("tribe_id", "parent_of", rec.alk_tribe_node_id.id),
                        ("active", "=", True),
                    ]
                )
                positions = positions.filtered(
                    lambda p, rec=rec: rec._alk_position_covers_area(p)
                )
                users = positions.mapped("user_id")
            rec.alk_representative_ids = users

    def _alk_position_covers_area(self, position):
        """A position covers the citizen if it has no area scope, or its area is
        the citizen's residential area or an ancestor of it."""
        self.ensure_one()
        if not position.area_id:
            return True
        citizen_area = self.area_id
        if citizen_area and citizen_area.parent_path and position.area_id.parent_path:
            return citizen_area.parent_path.startswith(position.area_id.parent_path)
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Assign a citizen number to individual registrants only.
            if (
                vals.get("is_registrant")
                and not vals.get("is_group")
                and not vals.get("alk_citizen_no")
            ):
                seq = self.env["ir.sequence"].next_by_code("alkathiry.citizen")
                if seq:
                    vals["alk_citizen_no"] = seq
        return super().create(vals_list)
