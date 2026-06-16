from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AlkathiryTribePosition(models.Model):
    """The generic, top-down leadership ladder — one engine for every structure.

    One record = a node in a ladder: a position title held by a person, scoped to
    an area, optionally reporting to a parent node. ONE engine serves tribes,
    unions, committees and organizations; the only thing that changes between them
    is the ``track`` and the title terminology ("the name changes, the machine is
    the same"). ``_parent_store`` over ``parent_position_id`` lets the node render
    as a top-down org chart (hierarchy view), and a ladder can be cloned to another
    country (structure only). Each ladder stays independent per country.
    """

    _name = "alkathiry.tribe.position"
    _description = "Alkathiry Position (Leadership Ladder)"
    _parent_name = "parent_position_id"
    _parent_store = True
    _order = "track_id, area_id, position_id"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True)
    active = fields.Boolean(default=True)

    track_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Ladder",
        required=True,
        index=True,
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:position-track')]",
        help="Which ladder this node sits in (sheikhs, aqils, union, committee, "
        "organization). A chain never crosses ladders.",
    )

    # The body this ladder belongs to — either a tribe node (registry group) or a
    # dedicated union/organization. Both optional: a ladder can also stand alone.
    tribe_id = fields.Many2one(
        "res.partner",
        string="Tribe (Body)",
        ondelete="cascade",
        index=True,
        domain="[('is_group', '=', True), ('is_registrant', '=', True)]",
        help="For tribal ladders: the tribe/lineage node this position belongs to.",
    )
    organization_id = fields.Many2one(
        "alkathiry.organization",
        string="Union / Organization (Body)",
        ondelete="cascade",
        index=True,
        help="For union/committee/organization ladders: the body this position "
        "belongs to.",
    )

    area_id = fields.Many2one(
        "spp.area",
        string="Place (Country / Governorate / City)",
        index=True,
        help="Where this node applies. Top of a national ladder = the country; "
        "lower nodes = governorate or city.",
    )
    position_id = fields.Many2one(
        "spp.vocabulary.code",
        string="Position / Title",
        required=True,
        domain="[('namespace_uri', '=', 'urn:alkathiry:vocab:position')]",
    )

    # The holder of the position — a person (individual registrant). user_id is the
    # optional matching system user (for the official-resolver / access).
    partner_id = fields.Many2one(
        "res.partner",
        string="Holder (Person)",
        index=True,
        domain="[('is_registrant', '=', True), ('is_group', '=', False)]",
        help="The accredited official / member who holds this position.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="System User",
        index=True,
        help="Optional system user matching the holder (used to resolve a "
        "citizen's officials).",
    )

    parent_position_id = fields.Many2one(
        "alkathiry.tribe.position",
        string="Reports To",
        ondelete="cascade",
        index=True,
        help="Higher node in the same ladder (e.g. a clan sheikh reports to the "
        "tribe sheikh; a deputy reports to the president).",
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("alkathiry.tribe.position", "parent_position_id", string="Subordinates")

    date_start = fields.Date()
    date_end = fields.Date()

    @api.depends("position_id", "partner_id", "area_id")
    def _compute_name(self):
        for rec in self:
            parts = [rec.position_id.display or ""]
            if rec.partner_id:
                parts.append(rec.partner_id.name or "")
            if rec.area_id:
                parts.append(rec.area_id.complete_name or "")
            rec.name = " — ".join(p for p in parts if p)

    @api.constrains("parent_position_id", "track_id")
    def _check_parent_same_track(self):
        for rec in self:
            parent = rec.parent_position_id
            if parent and parent.track_id and rec.track_id and parent.track_id != rec.track_id:
                raise ValidationError(
                    _("A position can only report to another position in the same ladder.")
                )

    @api.constrains("parent_position_id")
    def _check_parent_area_covers(self):
        for rec in self:
            parent = rec.parent_position_id
            if not parent or not parent.area_id or not rec.area_id:
                continue
            # The parent's place must cover (be an ancestor of, or equal to) the child's.
            child_path = rec.area_id.parent_path or ""
            parent_path = parent.area_id.parent_path or ""
            if parent_path and not child_path.startswith(parent_path):
                raise ValidationError(
                    _("The parent position's place must cover this position's place.")
                )

    @api.constrains("parent_position_id")
    def _check_no_position_cycle(self):
        for rec in self:
            if not rec._has_cycle():
                continue
            raise ValidationError(_("A position cannot report to itself (circular chain)."))

    def action_clone_to_country(self):
        """Open the wizard to clone this ladder (this node + its subordinates) to
        another country — structure only, officials left blank."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Clone Ladder to Another Country"),
            "res_model": "alkathiry.position.clone",
            "view_mode": "form",
            "target": "new",
            "context": {"default_source_position_id": self.id},
        }

    def copy_subtree(self, defaults=None, parent=None):
        """Recursively copy this node and all its subordinates.

        ``defaults`` overrides applied to every copied node (e.g. a new area_id and
        blanked holders). Returns the new root copy.
        """
        self.ensure_one()
        vals = dict(defaults or {})
        vals["parent_position_id"] = parent.id if parent else False
        new_node = self.copy(vals)
        for child in self.child_ids:
            child.copy_subtree(defaults=defaults, parent=new_node)
        return new_node
