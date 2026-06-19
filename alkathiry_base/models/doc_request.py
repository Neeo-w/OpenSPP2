from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DocRequest(models.Model):
    """A certification request that flows bottom-up through a beneficiary-built route.

    The beneficiary picks a hierarchy and builds a ``route`` (one chosen member per
    level), uploads documents and submits. The request is then assigned strictly to
    the next member in the route — no stage may be skipped — until it reaches the
    shared top (the Secretary General), where it becomes ``certified``. Every step
    is journalled (audit trail) and the next member is notified.
    """

    _name = "doc.request"
    _description = "Certification Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default="/")
    citizen_id = fields.Many2one(
        "res.partner",
        string="Beneficiary",
        required=True,
        index=True,
        tracking=True,
        domain="[('is_registrant', '=', True), ('is_group', '=', False)]",
    )
    hierarchy_id = fields.Many2one("doc.hierarchy", string="Hierarchy", required=True, tracking=True)
    country_id = fields.Many2one(related="hierarchy_id.country_id", store=True, index=True)
    area_id = fields.Many2one("spp.area", string="Beneficiary Place", index=True)
    route_ids = fields.One2many("doc.request.route", "request_id", string="Route")
    current_route_id = fields.Many2one("doc.request.route", string="Current Step", copy=False)
    current_level_id = fields.Many2one(related="current_route_id.level_id", store=True)
    current_documenter_id = fields.Many2one(related="current_route_id.documenter_id", store=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("in_review", "In Review"),
            ("certified", "Certified"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    document_ids = fields.Many2many("ir.attachment", string="Documents")
    log_ids = fields.One2many("doc.request.log", "request_id", string="Audit Trail")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("doc.request") or "/"
            if not vals.get("area_id") and vals.get("citizen_id"):
                citizen = self.env["res.partner"].browse(vals["citizen_id"])
                if citizen.area_id:
                    vals["area_id"] = citizen.area_id.id
        return super().create(vals_list)

    def action_build_route(self):
        """Open the route-builder wizard for this request."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("The route can only be built while the request is a draft."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Build Route"),
            "res_model": "doc.route.builder",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _log(self, action, note=False):
        self.ensure_one()
        self.env["doc.request.log"].create(
            {
                "request_id": self.id,
                "level_id": self.current_level_id.id or False,
                "user_id": self.env.user.id,
                "action": action,
                "note": note or False,
            }
        )

    def _notify_current(self):
        """Add the current member as follower and raise a to-do activity."""
        self.ensure_one()
        documenter = self.current_documenter_id
        user = documenter.user_id
        if not user:
            return
        self.message_subscribe(partner_ids=user.partner_id.ids)
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=_("Certification step: %s", self.current_level_id.name or ""),
        )

    def action_submit(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only a draft request can be submitted."))
        if not self.route_ids:
            raise UserError(_("Build the route before submitting."))
        # Constraint 3 + 4: complete route, every step has a chosen member.
        empty = self.route_ids.filtered(lambda r: not r.documenter_id)
        if empty:
            raise UserError(_("Every level in the route must have a chosen member."))
        first = self.route_ids.sorted("sequence")[0]
        self.write({"state": "in_review", "current_route_id": first.id})
        first.state = "current"
        self._log("submit")
        self._notify_current()
        return True

    def _assert_current_actor(self):
        self.ensure_one()
        documenter = self.current_documenter_id
        is_secretary = self.env.user.has_group("alkathiry_base.group_doc_secretary")
        if not is_secretary and documenter.user_id != self.env.user:
            raise UserError(
                _("Only the assigned member for the current step may act on this request.")
            )

    def action_approve(self, note=False):
        self.ensure_one()
        if self.state != "in_review":
            raise UserError(_("Only a request in review can be approved."))
        self._assert_current_actor()
        self._log("approve", note)
        current = self.current_route_id
        current.state = "approved"
        self.activity_feedback(["mail.mail_activity_data_todo"])
        # Mandatory sequence: advance ONLY to the immediate next step.
        nxt = self.route_ids.filtered(lambda r: r.sequence > current.sequence).sorted("sequence")
        if not nxt:
            self.write({"state": "certified", "current_route_id": False})
            self._log("certify")
            self.message_post(body=_("Request certified — route completed."))
            return True
        self.current_route_id = nxt[0]
        nxt[0].state = "current"
        self._notify_current()
        return True

    def action_reject(self, note=False):
        self.ensure_one()
        if self.state != "in_review":
            raise UserError(_("Only a request in review can be rejected."))
        self._assert_current_actor()
        if self.current_route_id:
            self.current_route_id.state = "rejected"
        self._log("reject", note)
        self.activity_feedback(["mail.mail_activity_data_todo"])
        self.write({"state": "rejected"})
        self.message_post(body=_("Request rejected at: %s", self.current_level_id.name or ""))
        return True


class DocRequestRoute(models.Model):
    """One step of a request's route: the member chosen for a given level."""

    _name = "doc.request.route"
    _description = "Certification Route Step"
    _order = "sequence, id"

    request_id = fields.Many2one("doc.request", required=True, ondelete="cascade", index=True)
    level_id = fields.Many2one("doc.level", string="Level", required=True)
    documenter_id = fields.Many2one("doc.documenter", string="Chosen Member")
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [("pending", "Pending"), ("current", "Current"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending",
    )

    @api.constrains("documenter_id", "level_id")
    def _check_member_in_level(self):
        for rec in self:
            if rec.documenter_id and rec.documenter_id.level_id != rec.level_id:
                raise ValidationError(_("The chosen member must belong to the step's level."))


class DocRequestLog(models.Model):
    """Immutable audit entry for every action taken on a request."""

    _name = "doc.request.log"
    _description = "Certification Audit Entry"
    _order = "date desc, id desc"

    request_id = fields.Many2one("doc.request", required=True, ondelete="cascade", index=True)
    level_id = fields.Many2one("doc.level", string="Level")
    user_id = fields.Many2one("res.users", string="Performed By", default=lambda self: self.env.user)
    action = fields.Selection(
        [
            ("submit", "Submitted"),
            ("approve", "Approved"),
            ("reject", "Rejected"),
            ("escalate", "Escalated"),
            ("certify", "Certified"),
        ],
        required=True,
    )
    date = fields.Datetime(default=fields.Datetime.now)
    note = fields.Text()
