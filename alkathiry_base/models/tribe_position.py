from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AlkathiryTribePosition(models.Model):
    """The leadership matrix for any community body, scoped per country.

    One row = (body x track x geographic scope) -> position + responsible
    official, optionally chained via ``parent_position_id``. The ``body`` is a
    registry group (``res.partner`` group): a tribe node, a union or an
    organization. The ``track`` separates the parallel ladders (sheikhs, aqils,
    union, organization) so a chain never mixes two ladders, and each ladder is
    independent per country (e.g. the Al-Kathir sheikhs ladder in Yemen vs the
    one in Saudi Arabia). The resolver matches a citizen's body + area against
    these rows to find their officials.
    """

    _name = "alkathiry.tribe.position"
    _description = "Alkathiry Position (Leadership Ladder)"
    _order = "track_id, tribe_id, area_id, position_id"

    name = fields.Char(compute="_compute_name", store=True)
    active = fields.Boolean(default=True)

    tribe_id = fields.Many2one(
        "res.partner",
        string="Body / Structure",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('is_group', '=', True), ('is_registrant', '=', True)]",
        help="The group this position belongs to: a tribe node, a union or an "
        "organization.",
    )
    track_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Track / Ladder",
        required=True,
        index=True,
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:position-track')]",
        help="Which parallel ladder this position sits in (sheikhs, aqils, "
        "union, organization). A chain never crosses tracks.",
    )
    area_id = fields.Many2one(
        "spp.area",
        string="Geographic Scope",
        index=True,
        help="Country/region this representation applies to. Empty = applies to "
        "the body everywhere.",
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
        help="The system user who holds this position for this body and scope.",
    )
    parent_position_id = fields.Many2one(
        "alkathiry.tribe.position",
        string="Reports To",
        help="Higher position in the same ladder (e.g. a clan sheikh reports to "
        "the tribe sheikh; a deputy reports to the president).",
    )
    date_start = fields.Date()
    date_end = fields.Date()

    @api.depends("track_id", "tribe_id", "area_id", "position_id")
    def _compute_name(self):
        for rec in self:
            parts = [rec.position_id.display or "", rec.tribe_id.name or ""]
            if rec.area_id:
                parts.append(rec.area_id.complete_name or "")
            rec.name = " — ".join(p for p in parts if p)

    @api.constrains("parent_position_id", "track_id")
    def _check_parent_same_track(self):
        for rec in self:
            parent = rec.parent_position_id
            if parent and parent.track_id and rec.track_id and parent.track_id != rec.track_id:
                raise ValidationError(
                    _("A position can only report to another position in the same ladder (track).")
                )

    @api.constrains("parent_position_id")
    def _check_parent_area_covers(self):
        for rec in self:
            parent = rec.parent_position_id
            if not parent or not parent.area_id or not rec.area_id:
                continue
            # The parent's scope must cover (be an ancestor of, or equal to) the child's.
            child_path = rec.area_id.parent_path or ""
            parent_path = parent.area_id.parent_path or ""
            if parent_path and not child_path.startswith(parent_path):
                raise ValidationError(
                    _("The parent position's area must cover this position's area.")
                )

    @api.constrains("parent_position_id")
    def _check_no_position_cycle(self):
        for rec in self:
            parent = rec.parent_position_id
            seen = {rec.id}
            while parent:
                if parent.id in seen:
                    raise ValidationError(_("A position cannot report to itself (circular chain)."))
                seen.add(parent.id)
                parent = parent.parent_position_id
