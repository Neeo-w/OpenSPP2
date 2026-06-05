import json
import logging

from odoo import http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)

API = "/api/v1"


def _json(data=None, error=None, status=200):
    """Build the platform's standard JSON envelope response."""
    body = {"success": error is None}
    if error is not None:
        body["error"] = error
    if data is not None:
        body["data"] = data
    return Response(json.dumps(body, default=str), status=status, content_type="application/json")


def _err(code, message, status=400):
    return _json(error={"code": code, "message": message}, status=status)


def _body():
    try:
        return json.loads(request.httprequest.data or "{}")
    except (ValueError, TypeError):
        return {}


def _bearer():
    auth = request.httprequest.headers.get("Authorization", "")
    return auth[7:].strip() if auth.startswith("Bearer ") else None


class AlkathiryMobileApi(http.Controller):
    """REST API gateway for the Beneficiary, Distributor and Verifier apps.

    All routes are metadata-driven: the apps render their UI from the JSON
    payloads returned here. Implements the redemption loop of Sequence Diagram
    26.1 (barcode → scan → OTP → confirm) with the local token service.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _svc(self, name):
        return request.env[name].sudo()

    def _auth_user(self):
        token = _bearer()
        if not token:
            return None
        return self._svc("alkathiry.token.service").verify_session(token)

    # ------------------------------------------------------------------
    # Authentication (OTP login)
    # ------------------------------------------------------------------
    @http.route(f"{API}/auth/request-otp", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def request_otp(self, **kw):
        phone = _body().get("phone")
        if not phone:
            return _err("PHONE_REQUIRED", "phone is required")
        partner = self._svc("res.partner").search(
            ["|", ("phone", "=", phone), ("mobile", "=", phone)], limit=1
        )
        if not partner:
            return _err("USER_NOT_FOUND", "No account for this phone", status=404)
        result = self._svc("alkathiry.token.service").issue_otp(partner)
        # The OTP itself is delivered out-of-band (SMS/FCM); only the handle returns.
        return _json({"token_uid": result["token_uid"], "expires_in": result["expires_in"]})

    @http.route(f"{API}/auth/verify-otp", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def verify_otp(self, **kw):
        data = _body()
        partner = self._svc("alkathiry.token.service").verify_otp(
            data.get("token_uid"), data.get("otp")
        )
        if not partner:
            return _err("OTP_INVALID", "Invalid or expired OTP", status=401)
        user = partner.user_ids[:1]
        if not user:
            return _err("NO_USER", "Account has no login user", status=403)
        session = self._svc("alkathiry.token.service").issue_session(user)
        return _json(
            {
                "access_token": session["access_token"],
                "expires_in": session["expires_in"],
                "partner": {"id": partner.id, "name": partner.name},
            }
        )

    # ------------------------------------------------------------------
    # Metadata for reflective Flutter rendering
    # ------------------------------------------------------------------
    @http.route(f"{API}/meta/registration", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def meta_registration(self, **kw):
        """Return the dynamic registration form schema for the Beneficiary app."""
        categories = self._svc("alkathiry.dynamic.category").search([("active", "=", True)])
        payload = []
        for cat in categories:
            payload.append(
                {
                    "id": cat.id,
                    "code": cat.code,
                    "name": cat.name,
                    "verification_method": cat.verification_method,
                    "fields": [
                        {
                            "key": f.technical_name,
                            "label": f.name,
                            "type": f.field_type,
                            "required": f.required,
                            "options": f.selection_options or [],
                            "validation": f.validation_rules or {},
                            "placeholder": f.placeholder or "",
                            "help": f.help_text or "",
                            "sequence": f.sequence,
                        }
                        for f in cat.field_ids.sorted("sequence")
                    ],
                }
            )
        return _json({"categories": payload})

    # ------------------------------------------------------------------
    # Beneficiary endpoints
    # ------------------------------------------------------------------
    @http.route(f"{API}/me", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def me(self, **kw):
        user = self._auth_user()
        if not user:
            return _err("UNAUTHORIZED", "Invalid session", status=401)
        p = user.partner_id
        return _json(
            {
                "id": p.id,
                "name": p.name,
                "status": p.alk_status,
                "category": p.alk_category_id.code,
                "area": p.alk_area_id.complete_name,
            }
        )

    @http.route(f"{API}/me/services", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def my_services(self, **kw):
        """Available eligible services with remaining quota (home-screen feed)."""
        user = self._auth_user()
        if not user:
            return _err("UNAUTHORIZED", "Invalid session", status=401)
        partner = user.partner_id
        engine = self._svc("alkathiry.distribution.engine")
        allocations = self._svc("alkathiry.service.allocation").search([("state", "=", "active")])
        items = []
        for alloc in allocations:
            ok, _msg = engine.evaluate_targeting(alloc, partner)
            if not ok:
                continue
            consumed = engine.consumed_in_window(partner, alloc)
            items.append(
                {
                    "allocation_id": alloc.id,
                    "service_id": alloc.service_id.id,
                    "service": alloc.service_id.name,
                    "distribution_model": alloc.service_id.distribution_model,
                    "quota": alloc.quota_per_beneficiary,
                    "remaining": (alloc.quota_per_beneficiary or 0.0) - consumed,
                }
            )
        return _json({"services": items})

    @http.route(f"{API}/me/barcode", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def my_barcode(self, **kw):
        user = self._auth_user()
        if not user:
            return _err("UNAUTHORIZED", "Invalid session", status=401)
        result = self._svc("alkathiry.token.service").issue_barcode(user.partner_id)
        return _json(result)

    # ------------------------------------------------------------------
    # Advertisements (decoupled from service execution)
    # ------------------------------------------------------------------
    @http.route(f"{API}/ads", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def ads(self, placement="beneficiary_home", **kw):
        user = self._auth_user()
        if not user:
            return _err("UNAUTHORIZED", "Invalid session", status=401)
        banners = self._svc("alkathiry.ad.campaign").serve_for(user.partner_id, placement)
        return _json({"ads": banners})

    @http.route(f"{API}/ads/<int:ad_id>/click", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def ad_click(self, ad_id, **kw):
        user = self._auth_user()
        if not user:
            return _err("UNAUTHORIZED", "Invalid session", status=401)
        ad = self._svc("alkathiry.ad.campaign").browse(ad_id)
        if not ad.exists():
            return _err("AD_NOT_FOUND", "Unknown campaign", status=404)
        ad.register_click()
        return _json({"clicked": True})

    # ------------------------------------------------------------------
    # Distributor redemption loop (Sequence Diagram 26.1)
    # ------------------------------------------------------------------
    def _distributor_for(self, user):
        return self._svc("alkathiry.distributor").search([("user_id", "=", user.id)], limit=1)

    @http.route(f"{API}/distributor/scan", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def distributor_scan(self, **kw):
        user = self._auth_user()
        if not user:
            return _err("UNAUTHORIZED", "Invalid session", status=401)
        distributor = self._distributor_for(user)
        if not distributor:
            return _err("NOT_DISTRIBUTOR", "User is not a distributor", status=403)
        data = _body()
        tokens = self._svc("alkathiry.token.service")
        partner = tokens.verify_barcode(data.get("barcode"))
        if not partner:
            return _err("BARCODE_INVALID", "Invalid or expired barcode", status=401)
        allocation = self._svc("alkathiry.service.allocation").browse(int(data.get("allocation_id", 0)))
        if not allocation.exists():
            return _err("ALLOCATION_NOT_FOUND", "Unknown allocation", status=404)
        quantity = float(data.get("quantity", 1.0))
        verdict = self._svc("alkathiry.distribution.engine").validate_claim(
            partner, allocation, distributor, quantity
        )
        if not verdict["ok"]:
            return _json({"eligible": False, "verdict": verdict})
        # Eligible → issue an OTP to the beneficiary device.
        otp = tokens.issue_otp(partner)
        return _json(
            {
                "eligible": True,
                "verdict": verdict,
                "otp_token_uid": otp["token_uid"],
                "otp_expires_in": otp["expires_in"],
                "beneficiary": {"id": partner.id, "name": partner.name},
            }
        )

    @http.route(f"{API}/distributor/confirm", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def distributor_confirm(self, **kw):
        user = self._auth_user()
        if not user:
            return _err("UNAUTHORIZED", "Invalid session", status=401)
        distributor = self._distributor_for(user)
        if not distributor:
            return _err("NOT_DISTRIBUTOR", "User is not a distributor", status=403)
        data = _body()
        tokens = self._svc("alkathiry.token.service")
        partner = tokens.verify_otp(data.get("otp_token_uid"), data.get("otp"))
        if not partner:
            return _err("OTP_INVALID", "Invalid or expired OTP", status=401)
        allocation = self._svc("alkathiry.service.allocation").browse(int(data.get("allocation_id", 0)))
        if not allocation.exists():
            return _err("ALLOCATION_NOT_FOUND", "Unknown allocation", status=404)
        quantity = float(data.get("quantity", 1.0))
        result = self._svc("alkathiry.distribution.engine").post_redemption(
            partner,
            allocation,
            distributor,
            quantity,
            otp_hash=tokens._hash(data.get("otp")),
            barcode_session_id=data.get("otp_token_uid"),
        )
        if not result["ok"]:
            return _json({"confirmed": False, "verdict": result.get("verdict")}, status=409)
        return _json({"confirmed": True, "transaction_number": result["transaction_number"]})
