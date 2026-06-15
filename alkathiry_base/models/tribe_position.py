from odoo import api, fields, models


class AlkathiryTribePosition(models.Model):
    """The tribal representation matrix: who leads which lineage node, where.

    One row = (lineage node x geographic scope) -> position + responsible
    official. Because the same clan exists in several countries, it can have a
    distinct row per geography (e.g. Al-Rawas: a Sheikh in Salalah/Oman and a
    Muqaddam in Seiyun/Yemen). The verification router resolves a citizen's
    official by matching the citizen's lineage node and area against these rows.
    """

    _name = "alkathiry.tribe.position"
    _description = "Alkathiry Tribal Position"
    _order = "tribe_id, area_id, position_id"

    name = fields.Char(compute="_compute_name", store=True)
    active = fields.Boolean(default=True)

    tribe_id = fields.Many2one(
        "alkathiry.tribe",
        string="Lineage Node",
        required=True,
        ondelete="cascade",
        index=True,
    )
    area_id = fields.Many2one(
        "spp.area",
        string="Geographic Scope",
        index=True,
        help="Country/region this representation applies to. Empty = applies to "
        "the lineage node everywhere.",
    )
    position_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Position",
        required=True,
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:position')]",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible Official",
        index=True,
        help="The system user who holds this position for this tribe and scope.",
    )
    parent_position_id = fields.Many2one(
        "alkathiry.tribe.position",
        string="Reports To",
        help="Higher position in the chain (e.g. a clan sheikh reports to the "
        "tribe sheikh).",
    )
    date_start = fields.Date()
    date_end = fields.Date()

    @api.depends("tribe_id", "area_id", "position_id")
    def _compute_name(self):
        for rec in self:
            parts = [rec.position_id.display or "", rec.tribe_id.name or ""]
            if rec.area_id:
                parts.append(rec.area_id.complete_name or "")
            rec.name = " — ".join(p for p in parts if p)
