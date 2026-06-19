from odoo import _, api, fields, models


class DocHierarchy(models.Model):
    """A concrete certification hierarchy bound to a country.

    The Secretary General (or a delegated committee) builds any number of these
    through the UI — no code. A hierarchy is just an ordered set of ``doc.level``
    stages; its ``type_id`` (tribal / aqils / union / administrative...) reuses the
    existing position-track vocabulary. Every hierarchy's route ultimately joins
    the shared global top (the Secretary General and his committees).
    """

    _name = "doc.hierarchy"
    _description = "Certification Hierarchy"
    _order = "country_id, name"

    name = fields.Char(required=True)
    type_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Hierarchy Type",
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:position-track')]",
        help="General classification (tribal / aqils / union / administrative...).",
    )
    country_id = fields.Many2one("res.country", string="Country", required=True, index=True)
    level_ids = fields.One2many("doc.level", "hierarchy_id", string="Levels")
    level_count = fields.Integer(compute="_compute_level_count")
    active = fields.Boolean(default=True)

    @api.depends("level_ids")
    def _compute_level_count(self):
        for rec in self:
            rec.level_count = len(rec.level_ids)

    def action_clone_to_country(self):
        """Open the wizard to replicate this hierarchy (levels + their structure)
        to another country — members left blank, ready for appointment."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Clone Hierarchy to Another Country"),
            "res_model": "doc.hierarchy.clone",
            "view_mode": "form",
            "target": "new",
            "context": {"default_source_hierarchy_id": self.id},
        }
