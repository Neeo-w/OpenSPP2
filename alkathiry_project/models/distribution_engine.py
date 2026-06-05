import logging
import secrets
from datetime import datetime, time

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

# Comparison operators supported by the JSON targeting DSL. Pure data-driven —
# no eval / exec is ever used, so admin-authored predicates are safe to run.
_LEAF_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and a > b,
    "ge": lambda a, b: a is not None and a >= b,
    "lt": lambda a, b: a is not None and a < b,
    "le": lambda a, b: a is not None and a <= b,
    "in": lambda a, b: a in (b or []),
    "not_in": lambda a, b: a not in (b or []),
    "contains": lambda a, b: bool(a) and b in a,
    "between": lambda a, b: bool(b) and len(b) == 2 and b[0] <= a <= b[1],
    "set": lambda a, b: bool(a),
    "exists": lambda a, b: a is not None,
}


class AlkDistributionEngine(models.AbstractModel):
    """Generic, high-performance distribution validation engine (Step 3).

    Pre-screens redemption claims coming from the Distributor app against the
    5-condition matrix (FR-DIS-03), evaluating dynamic JSON targeting predicates
    safely. Stateless: it reads state and returns a structured verdict; the
    immutable ledger posting happens at confirm time (Step 4).
    """

    _name = "alkathiry.distribution.engine"
    _description = "Alkathiry Distribution Validation Engine"

    # ------------------------------------------------------------------
    # Safe JSON predicate DSL
    # ------------------------------------------------------------------
    def evaluate_predicate(self, expr, ctx):
        """Recursively evaluate a JSON predicate against a context dict.

        Grammar::

            {"and": [<expr>, ...]} | {"or": [<expr>, ...]} | {"not": <expr>}
            {"field": "age", "op": "ge", "value": 18}   # leaf

        A falsy/empty expression means "no restriction" → True.
        """
        if not expr:
            return True
        if not isinstance(expr, dict):
            return False
        if "and" in expr:
            return all(self.evaluate_predicate(c, ctx) for c in expr["and"])
        if "or" in expr:
            return any(self.evaluate_predicate(c, ctx) for c in expr["or"])
        if "not" in expr:
            return not self.evaluate_predicate(expr["not"], ctx)
        if "field" in expr:
            op = _LEAF_OPS.get(expr.get("op", "eq"))
            if not op:
                _logger.warning("Unknown predicate operator: %s", expr.get("op"))
                return False
            try:
                return bool(op(ctx.get(expr["field"]), expr.get("value")))
            except (TypeError, ValueError):
                return False
        return False

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------
    def build_beneficiary_context(self, partner):
        """Flatten a beneficiary into a predicate-evaluation context."""
        age = None
        if partner.alk_birth_date:
            age = relativedelta(fields.Date.context_today(self), partner.alk_birth_date).years
        area = partner.alk_area_id
        return {
            "status": partner.alk_status,
            "category_code": partner.alk_category_id.code,
            "category_id": partner.alk_category_id.id,
            "area_id": area.id,
            "area_code": area.code or "",
            "area_path": area.parent_path or "",
            "gender": partner.alk_gender,
            "age": age,
            "family_count": partner.alk_family_count,
        }

    @api.model
    def _area_within(self, area, areas):
        """True if ``area`` is one of ``areas`` or any descendant (tree containment)."""
        if not areas:
            return True
        if not area or not area.parent_path:
            return False
        return any(a.parent_path and area.parent_path.startswith(a.parent_path) for a in areas)

    # ------------------------------------------------------------------
    # Targeting (categories + regions + JSON predicate)
    # ------------------------------------------------------------------
    def evaluate_targeting(self, allocation, partner):
        """FR-DIS-03 #2 — does the beneficiary satisfy the targeting criteria?"""
        service = allocation.service_id
        ctx = self.build_beneficiary_context(partner)

        if service.category_ids and partner.alk_category_id not in service.category_ids:
            return False, _("Beneficiary category is not targeted by this service.")

        areas = allocation.area_ids or service.area_ids
        if areas and not self._area_within(partner.alk_area_id, areas):
            return False, _("Beneficiary area is outside the targeted regions.")

        expr = allocation.targeting_expression or service.targeting_expression
        if not self.evaluate_predicate(expr, ctx):
            return False, _("Beneficiary does not satisfy the targeting predicate.")
        return True, _("Targeting satisfied.")

    # ------------------------------------------------------------------
    # Quota window
    # ------------------------------------------------------------------
    def _window_start(self, allocation):
        """Compute the start of the current reset window for quota accounting.

        Driven by the service's balance-type reset policy, not hardcoded:
        daily → today's start; periodic → now - N days; otherwise → allocation
        start (cumulative over the whole allocation).
        """
        balance_type = allocation.service_id.balance_type_id
        now = fields.Datetime.now()
        policy = balance_type.reset_policy if balance_type else "never"
        if policy == "daily":
            return datetime.combine(now.date(), time.min)
        if policy == "periodic" and balance_type.reset_period_days:
            return now - relativedelta(days=balance_type.reset_period_days)
        return allocation.date_start or datetime.combine(now.date(), time.min)

    def consumed_in_window(self, partner, allocation):
        """Sum successful redeemed quantity for this beneficiary in the window."""
        window_start = self._window_start(allocation)
        txns = self.env["alkathiry.transaction"].search(
            [
                ("partner_id", "=", partner.id),
                ("service_allocation_id", "=", allocation.id),
                ("transaction_type", "=", "redemption"),
                ("status", "=", "success"),
                ("posted_at", ">=", window_start),
            ]
        )
        return sum(txns.mapped("quantity")) or 0.0

    # ------------------------------------------------------------------
    # The 5-condition matrix (FR-DIS-03)
    # ------------------------------------------------------------------
    def validate_claim(self, partner, allocation, distributor, quantity=1.0):
        """Run the full pre-screen and return a structured, JSON-safe verdict."""
        conditions = []

        # #1 — beneficiary active per the dynamic workflow
        c1 = partner.alk_status == "active"
        conditions.append(
            {
                "code": "DIS-01",
                "label": _("Beneficiary active"),
                "ok": c1,
                "detail": _("Status: %s") % (partner.alk_status or "none"),
            }
        )

        # #2 — targeting (categories / regions / predicate)
        c2_ok, c2_msg = self.evaluate_targeting(allocation, partner)
        conditions.append(
            {"code": "DIS-02", "label": _("Targeting match"), "ok": c2_ok, "detail": c2_msg}
        )

        # #3 — allocation active & current on the timeline
        now = fields.Datetime.now()
        c3 = (
            allocation.state == "active"
            and (not allocation.date_start or allocation.date_start <= now)
            and (not allocation.date_end or allocation.date_end >= now)
        )
        conditions.append(
            {
                "code": "DIS-03",
                "label": _("Allocation current"),
                "ok": c3,
                "detail": _("State: %s") % allocation.state,
            }
        )

        # #4 — unspent quota in the current reset window
        consumed = self.consumed_in_window(partner, allocation)
        remaining_quota = (allocation.quota_per_beneficiary or 0.0) - consumed
        c4 = remaining_quota >= quantity
        conditions.append(
            {
                "code": "DIS-04",
                "label": _("Unspent quota"),
                "ok": c4,
                "detail": _("Remaining %(rem)s of %(quota)s")
                % {"rem": remaining_quota, "quota": allocation.quota_per_beneficiary},
            }
        )

        # #5 — distributor has enough stock on hand
        dist_alloc = self.env["alkathiry.distributor.allocation"].search(
            [
                ("distributor_id", "=", distributor.id),
                ("service_allocation_id", "=", allocation.id),
            ],
            limit=1,
        )
        on_hand = dist_alloc.quantity_on_hand if dist_alloc else 0.0
        c5 = bool(dist_alloc) and on_hand >= quantity
        conditions.append(
            {
                "code": "DIS-05",
                "label": _("Distributor stock"),
                "ok": c5,
                "detail": _("On hand: %s") % on_hand,
            }
        )

        failed = [c["code"] for c in conditions if not c["ok"]]
        return {
            "ok": not failed,
            "quantity": quantity,
            "remaining_quota": remaining_quota,
            "distributor_on_hand": on_hand,
            "conditions": conditions,
            "failed": failed,
        }

    # ------------------------------------------------------------------
    # Redemption posting (confirm step) — immutable double-entry
    # ------------------------------------------------------------------
    def post_redemption(self, partner, allocation, distributor, quantity=1.0,
                        otp_hash=None, barcode_session_id=None):
        """Post an immutable redemption to the ledger and update derived state.

        Re-validates the claim under a row lock-free read, then writes:
          * a debit + credit pair on the immutable transaction ledger (Mifos-style),
          * a debit wallet movement and balance decrement for the beneficiary,
          * the distributor stock decrement,
          * the multi-tier commission split.
        """
        verdict = self.validate_claim(partner, allocation, distributor, quantity)
        if not verdict["ok"]:
            return {"ok": False, "verdict": verdict}

        service = allocation.service_id
        balance_type = service.balance_type_id
        # In-kind quota redemptions are quantity-based; monetary pricing (amount > 0)
        # can be layered on later without changing the ledger structure.
        amount = 0.0
        move_uid = self.env["ir.sequence"].next_by_code("alkathiry.move") or secrets.token_hex(8)

        # Commission split: distributor rate + committee (provider fee) rate.
        dist_alloc = self.env["alkathiry.distributor.allocation"].search(
            [("distributor_id", "=", distributor.id),
             ("service_allocation_id", "=", allocation.id)], limit=1)
        commission_distributor = (dist_alloc.commission_rate or 0.0) / 100.0 * amount
        commission_committee = (
            (service.provider_id.service_fee_rate or 0.0) / 100.0 * amount
        )

        txn_model = self.env["alkathiry.transaction"].sudo()
        common = {
            "move_uid": move_uid,
            "transaction_type": "redemption",
            "partner_id": partner.id,
            "distributor_id": distributor.id,
            "service_id": service.id,
            "service_allocation_id": allocation.id,
            "balance_type_id": balance_type.id if balance_type else False,
            "amount": amount,
            "quantity": quantity,
            "status": "success",
            "barcode_session_id": barcode_session_id,
            "otp_hash": otp_hash,
            "commission_distributor": commission_distributor,
            "commission_committee": commission_committee,
        }
        wallet = self._get_or_create_wallet(partner)
        debit = txn_model.create(dict(
            common,
            transaction_number=self.env["ir.sequence"].next_by_code("alkathiry.transaction"),
            direction="debit",
            wallet_id=wallet.id,
        ))
        txn_model.create(dict(
            common,
            transaction_number=self.env["ir.sequence"].next_by_code("alkathiry.transaction"),
            direction="credit",
        ))

        # Wallet movement + balance decrement (in-kind quota consumption).
        if balance_type:
            balance = self.env["alkathiry.balance"].sudo().search(
                [("wallet_id", "=", wallet.id), ("balance_type_id", "=", balance_type.id)],
                limit=1)
            if balance:
                self.env["alkathiry.wallet.movement"].sudo().create({
                    "wallet_id": wallet.id,
                    "partner_id": partner.id,
                    "movement_type": "debit",
                    "amount": quantity,
                    "balance_type_id": balance_type.id,
                    "reason": _("Redemption %s") % debit.transaction_number,
                    "related_transaction_id": debit.id,
                })
                balance.current_amount = balance.current_amount - quantity

        # Distributor stock decrement.
        if dist_alloc:
            dist_alloc.quantity_distributed = dist_alloc.quantity_distributed + quantity

        return {"ok": True, "transaction_number": debit.transaction_number, "verdict": verdict}

    def _get_or_create_wallet(self, partner):
        wallet = self.env["alkathiry.wallet"].sudo().search(
            [("partner_id", "=", partner.id)], limit=1)
        if not wallet:
            wallet = self.env["alkathiry.wallet"].sudo().create({"partner_id": partner.id})
        return wallet
