from odoo import _, fields, models
from odoo.exceptions import UserError


class DocRouteBuilder(models.TransientModel):
    """Builds a request's route bottom-up by walking ``parent_level_id``.

    Starting from the beneficiary's entry level, it climbs the chain, auto-picking
    the single member of each level and leaving multi-member levels blank for the
    beneficiary to choose afterward. The shared global top (Secretary General and
    his committees) is always appended, so every route ends at the same place.
    """

    _name = "doc.route.builder"
    _description = "Certification Route Builder"

    request_id = fields.Many2one("doc.request", required=True, ondelete="cascade")
    hierarchy_id = fields.Many2one(related="request_id.hierarchy_id")
    start_level_id = fields.Many2one(
        "doc.level",
        string="Entry Level (Applicant)",
        required=True,
        domain="[('hierarchy_id', '=', hierarchy_id)]",
        help="The beneficiary's own level. The route is built from the level above "
        "it up to the shared top.",
    )

    def _default_start_level(self, hierarchy):
        levels = hierarchy.level_ids.filtered(lambda level: not level.is_global).sorted("sequence")
        return levels[:1]

    def action_build(self):
        self.ensure_one()
        request = self.request_id
        citizen_area = request.area_id
        request.route_ids.unlink()
        steps = []
        seq = 0
        visited = set()

        node = self.start_level_id.parent_level_id
        while node and node.id not in visited:
            visited.add(node.id)
            seq += 1
            steps.append(self._make_step(node, citizen_area, seq))
            node = node.parent_level_id

        # Always append the shared global top, in order, if not already reached.
        globals_ = self.env["doc.level"].search([("is_global", "=", True)], order="sequence")
        for glevel in globals_:
            if glevel.id in visited:
                continue
            visited.add(glevel.id)
            seq += 1
            steps.append(self._make_step(glevel, citizen_area, seq))

        if not steps:
            raise UserError(_("No higher levels found above the entry level."))
        request.write({"route_ids": [(0, 0, s) for s in steps]})
        return {
            "type": "ir.actions.act_window",
            "res_model": "doc.request",
            "res_id": request.id,
            "view_mode": "form",
            "target": "current",
        }

    def _make_step(self, level, citizen_area, seq):
        members = level.eligible_documenters(citizen_area)
        if not members:
            raise UserError(
                _("Level '%s' has no eligible member — cannot build a complete route.", level.name)
            )
        chosen = members if len(members) == 1 else members.browse()
        return {
            "level_id": level.id,
            "documenter_id": chosen.id if chosen else False,
            "sequence": seq,
        }


class DocHierarchyClone(models.TransientModel):
    """Clone a whole hierarchy (levels + their links) to another country.

    Replicates the structure so the same ladder can serve another country; members
    are cleared by default, ready for appointment. Reuses the same clone idea as
    the org-chart ladder.
    """

    _name = "doc.hierarchy.clone"
    _description = "Clone Hierarchy to Another Country"

    source_hierarchy_id = fields.Many2one("doc.hierarchy", required=True)
    target_country_id = fields.Many2one("res.country", string="Target Country", required=True)
    keep_members = fields.Boolean(string="Keep members", default=False)

    def action_clone(self):
        self.ensure_one()
        source = self.source_hierarchy_id
        new_hierarchy = source.copy(
            {
                "name": _("%s (copy)", source.name),
                "country_id": self.target_country_id.id,
                "level_ids": [],
            }
        )
        # Copy levels first (without parent links), then remap parents.
        old_to_new = {}
        for level in source.level_ids.sorted("sequence"):
            vals = {
                "hierarchy_id": new_hierarchy.id,
                "parent_level_id": False,
                "documenter_ids": [],
            }
            new_level = level.copy(vals)
            old_to_new[level.id] = new_level
            if not self.keep_members:
                continue
            for member in level.documenter_ids:
                member.copy({"level_id": new_level.id})
        for level in source.level_ids:
            if level.parent_level_id and level.parent_level_id.id in old_to_new:
                old_to_new[level.id].parent_level_id = old_to_new[level.parent_level_id.id].id
        return {
            "type": "ir.actions.act_window",
            "res_model": "doc.hierarchy",
            "res_id": new_hierarchy.id,
            "view_mode": "form",
            "target": "current",
        }
