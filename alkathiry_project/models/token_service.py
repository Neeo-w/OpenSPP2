import hashlib
import logging
import secrets
from datetime import timedelta

import jwt

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

_CONFIG_SECRET_KEY = "alkathiry_project.jwt_secret"
_ALGO = "HS256"


class AlkTokenService(models.AbstractModel):
    """Local identity-token service (MOSIP-inspired).

    Issues and verifies the encrypted/signed tokens used across the platform:
    the beneficiary barcode JWT, the redemption OTP, and the mobile session token.
    Every token is mirrored by an ``alkathiry.identity.token`` row so it can be
    revoked, expired or audited. No external identity cloud is contacted.
    """

    _name = "alkathiry.token.service"
    _description = "Alkathiry Token Service"

    # ------------------------------------------------------------------
    # Secret management
    # ------------------------------------------------------------------
    @api.model
    def _secret(self):
        params = self.env["ir.config_parameter"].sudo()
        secret = params.get_param(_CONFIG_SECRET_KEY)
        if not secret:
            secret = secrets.token_urlsafe(48)
            params.set_param(_CONFIG_SECRET_KEY, secret)
        return secret

    @api.model
    def _hash(self, value):
        return hashlib.sha256((value or "").encode()).hexdigest()

    # ------------------------------------------------------------------
    # Issuance
    # ------------------------------------------------------------------
    @api.model
    def _create_token_record(self, partner, token_type, ttl_seconds, payload_hash=None, scope=None):
        now = fields.Datetime.now()
        return self.env["alkathiry.identity.token"].sudo().create(
            {
                "token_uid": secrets.token_urlsafe(16),
                "partner_id": partner.id,
                "token_type": token_type,
                "payload_hash": payload_hash,
                "issued_at": now,
                "expires_at": now + timedelta(seconds=ttl_seconds),
                "state": "active",
                "scope": scope or {},
            }
        )

    @api.model
    def _encode(self, claims, ttl_seconds):
        now = fields.Datetime.now()
        payload = dict(claims)
        payload.update(
            {
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
            }
        )
        return jwt.encode(payload, self._secret(), algorithm=_ALGO)

    @api.model
    def issue_barcode(self, partner):
        """Issue the short-lived barcode JWT shown by the beneficiary app."""
        ttl = self.env.company.alk_barcode_token_ttl_seconds or 300
        rec = self._create_token_record(partner, "barcode", ttl, scope={"aud": "distributor"})
        token = self._encode(
            {"sub": partner.id, "jti": rec.token_uid, "typ": "barcode"}, ttl
        )
        return {"token": token, "token_uid": rec.token_uid, "expires_in": ttl}

    @api.model
    def issue_otp(self, partner):
        """Issue a numeric OTP to the beneficiary device for redemption confirm."""
        ttl = self.env.company.alk_otp_ttl_seconds or 120
        otp = f"{secrets.randbelow(10**6):06d}"
        rec = self._create_token_record(
            partner, "otp", ttl, payload_hash=self._hash(otp), scope={"aud": "redemption"}
        )
        # Delivery (SMS/FCM) is handled by the messaging layer; logged for now.
        _logger.info("OTP issued for partner %s (token %s)", partner.id, rec.token_uid)
        return {"otp": otp, "token_uid": rec.token_uid, "expires_in": ttl}

    @api.model
    def issue_session(self, user):
        """Issue a mobile session JWT (24h) bound to a user."""
        ttl = 24 * 3600
        token = self._encode(
            {"sub": user.partner_id.id, "uid": user.id, "typ": "session"}, ttl
        )
        return {"access_token": token, "expires_in": ttl}

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    @api.model
    def _decode(self, token):
        try:
            return jwt.decode(token, self._secret(), algorithms=[_ALGO])
        except jwt.PyJWTError as exc:
            _logger.info("JWT decode failed: %s", exc)
            return None

    @api.model
    def verify_barcode(self, token):
        """Return the beneficiary partner for a valid, unconsumed barcode token."""
        claims = self._decode(token)
        if not claims or claims.get("typ") != "barcode":
            return None
        rec = self.env["alkathiry.identity.token"].sudo().search(
            [("token_uid", "=", claims.get("jti")), ("token_type", "=", "barcode")], limit=1
        )
        if not rec or rec.state != "active" or rec.expires_at < fields.Datetime.now():
            return None
        return self.env["res.partner"].browse(claims["sub"]).exists()

    @api.model
    def verify_otp(self, token_uid, otp):
        """Validate and consume a redemption OTP. Returns the partner or None."""
        rec = self.env["alkathiry.identity.token"].sudo().search(
            [("token_uid", "=", token_uid), ("token_type", "=", "otp")], limit=1
        )
        if not rec or rec.state != "active" or rec.expires_at < fields.Datetime.now():
            return None
        if rec.payload_hash != self._hash(otp):
            return None
        rec.write({"state": "consumed", "consumed_at": fields.Datetime.now()})
        return rec.partner_id

    @api.model
    def verify_session(self, token):
        """Return the user for a valid session token, else None."""
        claims = self._decode(token)
        if not claims or claims.get("typ") != "session":
            return None
        return self.env["res.users"].browse(claims["uid"]).exists()
