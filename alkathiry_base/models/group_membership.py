from odoo import fields, models


class SppGroupMembership(models.Model):
    """Surface the body's type and country on the membership.

    Lets the citizen's profile show a single unified "Affiliations" list that
    groups every membership by the kind of body (tribe / union / organization /
    activity) and its country — without a separate field per type.
    """

    _inherit = "spp.group.membership"

    group_type_id = fields.Many2one(
        related="group.group_type_id",
        string="Body Type",
        store=True,
        index=True,
    )
    group_area_id = fields.Many2one(
        related="group.area_id",
        string="Country / Area",
        store=True,
    )
