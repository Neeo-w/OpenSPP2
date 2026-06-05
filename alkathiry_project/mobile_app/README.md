# Alkathiry Mobile App (Flutter foundation)

A **metadata-driven** Flutter client. Screens are built at runtime from JSON
payloads returned by the Odoo gateway — no generated models, no hardcoded forms —
so changes made by the Central Committee in the Odoo Admin UI flow straight to the
apps. Kept dependency-light (`http` only) to stay compatible with on-device IDEs
(AIDE / Android IDE).

## Structure
- `lib/api_client.dart` — REST client + JSON envelope handling + bearer session.
- `lib/dynamic_form.dart` — **reflective renderer**: turns a list of field
  descriptors into widgets (text/number/date/dropdown/switch/upload).
- `lib/main.dart` — role hub + screens:
  - Registration (renders from `GET /meta/registration`).
  - Login (OTP → session JWT).
  - Beneficiary home (services/quota + barcode).
  - Distributor console (Sequence Diagram 26.1: scan → OTP → confirm).

## Run
1. Start Odoo with `alkathiry_project` installed.
2. Set `kBaseUrl` in `lib/main.dart` (emulator: `http://10.0.2.2:8069`).
3. `flutter pub get && flutter run`.

## Production add-ons (desktop build)
- `mobile_scanner` for live camera barcode scanning (replaces manual token entry).
- `qr_flutter` to render the beneficiary barcode as a QR image.
- `flutter_secure_storage` to persist the session token.
- Offline-to-online queue (CommCare/ODK-style) for the distributor confirm path.
