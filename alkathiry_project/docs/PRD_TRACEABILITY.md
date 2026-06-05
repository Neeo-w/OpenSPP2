# Alkathiry Platform — PRD Scenario ↔ Code Traceability

This document maps every PRD section, scenario, functional-requirement group and
API endpoint to the current `alkathiry_project` implementation, and states how
compatible each is with the code that exists **today**.

> Scope note: only the **data layer (Phase 0 / Step 1)** has been built so far.
> Engines (verification state machine, validation matrix, reset, financial
> posting), REST controllers, and the Flutter apps are intentionally deferred
> until sign-off. The "Status" column reflects that reality honestly.

**Status legend**

| Symbol | Meaning |
|---|---|
| ✅ | Data model fully in place; the scenario's persistence needs are covered |
| 🔶 | Data model in place, but the **behaviour** (engine/controller/API) is a later step |
| ⏳ | Not started — belongs to a later phase (controllers / Flutter / reports) |
| ❗ | Gap or open question that needs a decision before building |

> Source caveat: the three PRDs are in Arabic and were text-mined. The SQL schema
> (§24.2), API list (§25), FR codes and sequence diagram (§26.1) extracted
> cleanly; Arabic prose did not. Rows derived from Arabic descriptions are marked ❗
> "confirm".

---

## 1. Personas → roles in code

The PRD defines 5 personas (§ Personas 1–5). They map onto dynamic verifier tiers
and account types rather than hardcoded roles.

| Persona (PRD) | Code representation | Status |
|---|---|---|
| Beneficiary (المستفيد) | `res.partner` ext (`alk_is_beneficiary`, `alk_status`, `alk_dynamic_values`) | ✅ |
| Distributor (الموزّع) | `alkathiry.distributor` (+ `distributor.allocation`) | ✅ |
| Verifier — Aqil / Sheikh / Grand Sheikh | `alkathiry.verification.stage.config` + `verifier.role.assignment` (multi-role, multi-scope, FR-VER-05) | ✅ |
| Service Provider (مزوّد الخدمة) | `alkathiry.service.provider` | ✅ |
| Central Committee / Admin | terminal stage (`is_committee`) + Odoo `base.group_system` | ✅ |

Because tiers are **records**, the 4-tier Aqil→Sheikh→Grand Sheikh→Committee
chain can be re-ordered/extended without code (Absolute Dynamism mandate).

---

## 2. Use-case scenarios (UC-01 … UC-07)

The PRD §9 carries 7 detailed use cases. Below each is mapped to the data it
touches and the engine/controller work it will later need.

### UC-01 — New beneficiary registration  ✅ data / 🔶 flow
Flow: open app → choose language → enter mobile → OTP → complete dynamic profile
→ enters verification pipeline.

| Step | Backing model | Status |
|---|---|---|
| OTP issue/verify | `alkathiry.identity.token` (`token_type=otp`, `expires_at`) | ✅ data · 🔶 `POST /auth/register`,`/verify-otp` |
| Dynamic profile form | `dynamic.category` + `category.field` → `res.partner.alk_dynamic_values` | ✅ |
| Enter pipeline | `verification.request` (state `draft→in_progress`), `current_stage_id` | ✅ data · 🔶 state machine (Step 2) |

### UC-02 — Hierarchical verification (approve/reject/escalate)  🔶
Flow: verifier sees pending → approve advances to next tier; N rejections escalate
to committee (BR-VER-03).

| Element | Backing model | Status |
|---|---|---|
| Pending queue per scope | `verifier.role.assignment` (stage × scope) | ✅ data · 🔶 `GET /verifier/pending` |
| Per-tier decision | `verification.request.line` (`decision`, `verifier_id`) | ✅ |
| Consecutive-rejection escalation | `verification.request.consecutive_rejections` + `res.company.alk_max_consecutive_rejections` | ✅ data · 🔶 engine |
| SLA reminder / auto-escalate | `stage_entered_at`,`reminder_sent_at` + company `alk_sla_*` | ✅ data · 🔶 cron |

### UC-03 — Distribution / redemption loop (Sequence Diagram §26.1)  🔶
See §5 below for the step-by-step mapping. Data fully modelled; the 5-condition
validation matrix and OTP loop are Step 3 + controllers.

### UC-04 — Wallet & withdrawal  🔶
| Element | Backing model | Status |
|---|---|---|
| Balances per type | `alkathiry.wallet` + `balance` (dynamic `balance.type.config`) | ✅ |
| Movement history incl. reset losses | `alkathiry.wallet.movement` (`credit/debit/reset_loss`) | ✅ data · 🔶 reset cron |
| Withdrawal request | ❗ no dedicated model yet — see Gaps (§8) | ❗ |

### UC-05 — Service creation & approval (provider → committee → distributor)  🔶
| Element | Backing model | Status |
|---|---|---|
| Provider catalog | `service.provider` | ✅ |
| Service lifecycle (`draft→pending_committee→approved→…→active`) | `alkathiry.service.state` | ✅ data · 🔶 `POST /provider/services`, `/admin/services/{id}/approve` |
| Quota & targeting | `service` (`total/remaining_quantity`, `targeting_expression`, `area_ids`, `category_ids`) | ✅ |
| Distributor allocation + shipment | `distributor.allocation` (`shipment_status`,`commission_rate`) | ✅ data · 🔶 `/distributor/confirm-shipment` |

### UC-06 — Delegation / family proxy redemption (FR-DEL)  🔶
| Element | Backing model | Status |
|---|---|---|
| Delegation grant (once/service/permanent) | `alkathiry.delegation` | ✅ data · 🔶 `POST /me/delegations` |
| Proxy recorded on ledger | `transaction.delegated_for_partner_id`, `delegation_id` | ✅ |
| Family linkage | `res.partner.alk_family_count` + `delegation.is_family` | 🔶 family graph (see Gaps) |

### UC-07 — Ads / certificates / reports  🔶 / ⏳
| Element | Backing model | Status |
|---|---|---|
| Targeted banners | `ad.campaign` (`ad_type`, `targeting_expression`, counters) | ✅ data · 🔶 `POST /provider/campaigns` |
| Certificate issuance | `credential` + `credential.template` (Sunbird-style) | ✅ data · 🔶 issuance engine |
| Reports / dashboards | derived from `transaction` ledger | ⏳ Step 5 |

> ❗ **Confirm:** UC-01 is verified as registration. UC-02…07 titles were inferred
> from the API surface and schema because the PRD prose is Arabic. Please confirm
> the exact UC ordering/titles so this section is authoritative.

---

## 3. Functional-requirement groups (§ FR matrix)

20 FR groups were detected. Coverage of the **data** each group depends on:

| Group (count) | Likely scope | Primary models | Status |
|---|---|---|---|
| FR-AUTH (9) | Auth: register/OTP/JWT/login | `identity.token`, `res.partner` | ✅ data · 🔶 controllers |
| FR-USE (7) | User management | `res.partner` ext | ✅ data · 🔶 |
| FR-PRF (6) | Profile | `res.partner` + `category.field` | ✅ data · 🔶 |
| FR-VER (9) | Hierarchical verification | `verification.stage.config`, `verification.request(.line)`, `verifier.role.assignment` | ✅ data · 🔶 engine |
| FR-CAT (5) | Dynamic categories | `dynamic.category`, `category.field` | ✅ |
| FR-SVC (7) | Services | `service`, `service.provider`, `service.allocation` | ✅ data · 🔶 |
| FR-DIS (9) | Distribution / redemption | `distributor(.allocation)`, `transaction`, `identity.token` | ✅ data · 🔶 validation engine |
| FR-WAL (7) | Wallet | `wallet`, `balance`, `wallet.movement` | ✅ data · 🔶 reset cron |
| FR-FIN (4) | Finance / accounting | `transaction`, `commission.rule` | 🔶 posting + reports (Step 5) |
| FR-DEL (5) | Delegation | `delegation`, `transaction.delegated_for_partner_id` | ✅ data · 🔶 |
| FR-ADS (6) | Advertisements | `ad.campaign`, `service.provider` | ✅ data · 🔶 |
| FR-LFE (5) | Lifecycle (deceased/archive) | `res.partner.alk_status` (`deceased`,`archived`) + timestamps | ✅ data · 🔶 |
| FR-ADM (8) | Admin dashboard / config | all config models | ✅ data · ⏳ views |
| FR-RPT (7) | Reports | `transaction`, `audit.log` | ⏳ Step 5 |
| FR-SEC / NFR-SEC (10) | Security & immutability | DB triggers on `transaction`,`audit.log`; hashed national ID; encrypted tokens | ✅ (triggers live) · 🔶 OAuth2/JWT |
| FR-OFF (4) | Offline sync | (Flutter) | ⏳ Step 4 |
| FR-WEB (4) | Web portal | (frontend) | ⏳ |
| FR-AVL (5) | ❗ confirm (availability?) | — | ❗ |
| FR-CMP (4) | ❗ confirm (complaints/grievance?) | — | ❗ |
| FR-SCL (5) | ❗ confirm (social?) | — | ❗ |

> ❗ **Confirm:** FR-AVL, FR-CMP, FR-SCL meanings are uncertain (Arabic). If any
> require their own entities (e.g. a complaints/grievance table), they are not yet
> modelled — flag them and I will add models.

---

## 4. API surface (§25) → backing models

Every documented endpoint, and the model that will serve it. (All controllers ⏳
pending sign-off.)

| Endpoint | Backing model(s) | Data ready |
|---|---|---|
| `POST /auth/register`, `/verify-otp`, `/login`, `/refresh`, `/logout`, `/forgot-password` | `identity.token`, `res.partner` | ✅ |
| `GET /me`, `/me/services`, `/me/wallet`, `/me/transactions`, `/me/certificates`, `/me/family` | `res.partner`, `service`, `wallet`, `transaction`, `credential` | ✅ |
| `GET /me/barcode` | `identity.token` (`barcode`, TTL = `alk_barcode_token_ttl_seconds`) | ✅ |
| `POST /me/withdraw-request`, `/me/transfer-request` | ❗ withdrawal/transfer model missing | ❗ |
| `POST /me/delegations` | `delegation` | ✅ |
| `GET /distributor/services`, `/transactions`, `/commissions` | `distributor.allocation`, `transaction` | ✅ |
| `POST /distributor/scan` | `identity.token` + `transaction` (validation matrix) | ✅ data · 🔶 engine |
| `POST /distributor/confirm` | `transaction` (immutable insert) + `wallet.movement` | ✅ |
| `POST /distributor/confirm-shipment` | `distributor.allocation.shipment_status` | ✅ |
| `GET /verifier/pending`, `/users/{id}`, `POST .../approve`, `.../reject` | `verification.request(.line)`, `verifier.role.assignment` | ✅ data · 🔶 engine |
| `POST /provider/services`, `GET /provider/services/{id}/report`, `POST /provider/campaigns` | `service`, `transaction`, `ad.campaign` | ✅ data |
| `GET /admin/dashboard`, `/admin/users`, `POST /admin/wallet/credit`, `/admin/services/{id}/approve`, `GET /admin/audit-log`, `/admin/reports/{type}`, `POST /admin/notifications/broadcast` | all + `audit.log` | ✅ data · ⏳ notifications model (§8) |

---

## 5. Sequence Diagram §26.1 — redemption loop, step by step

| # | Step | Model / field | Status |
|---|---|---|---|
| 1 | Beneficiary shows dynamic barcode (encrypted JWT, default 5 min) | `identity.token` `token_type=barcode`, `expires_at`, company `alk_barcode_token_ttl_seconds` | ✅ data |
| 2 | Distributor `POST /scan` | `transaction.barcode_session_id` links the session | ✅ data · 🔶 endpoint |
| 3a | 5-condition eligibility check (FR-DIS-03) | beneficiary `alk_status` (#1), category/region predicate (#2), `service.allocation` window (#3), unspent quota via `transaction` quota index (#4), distributor `quantity_on_hand` (#5) | 🔶 engine (Step 3) |
| 3b | Issue OTP to beneficiary device (default 2 min) | `identity.token` `token_type=otp`, company `alk_otp_ttl_seconds` | ✅ data |
| 4 | Distributor `POST /confirm` with OTP | `transaction.otp_hash`, immutable insert, `commission_distributor/committee` | ✅ data · 🔶 endpoint |
| 5 | Ledger entry is unalterable | `BEFORE UPDATE OR DELETE` trigger on `alkathiry_transaction` | ✅ **live** |

---

## 6. Data schema §24.2 → model mapping (parity check)

| PRD table | Model | Notes |
|---|---|---|
| `users` | `res.partner` (ext) | enums → dynamic (`category`, `geo.area`); national ID hashed+encrypted |
| `verification_steps` | `verification.request.line` | `stage_number` → dynamic `stage_id` |
| `wallets` | `wallet` + `balance` | fixed columns → dynamic `balance.type.config` |
| `wallet_movements` | `wallet.movement` | ✅ incl. `reset_loss` |
| `service_providers` | `service.provider` | ✅ |
| `services` | `service` | ✅ incl. components/quantities/withdrawal_limit |
| `service_allocations` | `service.allocation` + `distributor.allocation` | split: timeline window vs. distributor stock |
| `transactions` | `transaction` | ✅ immutable + hash chain |
| `audit_log` | `audit.log` | ✅ append-only |
| `delegations` | `delegation` | ✅ |
| `ad_campaigns` | `ad.campaign` | ✅ |
| `certificates` | `credential` (+ `template`) | ✅ Sunbird-style dynamic templating |
| `tribes`, `districts` (referenced) | `geo.area` + `geo.area.level` | fixed tables → dynamic tree |

---

## 7. Dynamism mandate — where fixed PRD enums became configurable

| PRD fixed structure | Made dynamic by | 
|---|---|
| `stage` enum (pending_aqil…committee) | `verification.stage.config` (N-tier, re-orderable) |
| `balance_cumulative/daily/periodic` columns | `balance.type.config` + `balance` rows |
| `tribes` / `districts` tables | `geo.area` self-referencing tree + `geo.area.level` |
| category membership | `dynamic.category` + `category.field` |
| targeting (target_categories/regions arrays) | JSON `targeting_expression` + `eligibility_domain` |
| timing thresholds (OTP/barcode TTL, rejection X, SLA T) | `res.company.alk_*` parameters |

Stable taxonomies (`provider_type`, `service_type`, `ad_type`) remain `Selection`;
they can be promoted to config models on request.

---

## 8. Open gaps & decisions needed (❗)

1. **Withdrawal / transfer requests** — `POST /me/withdraw-request` and
   `/me/transfer-request` have no dedicated model yet. Recommend
   `alkathiry.withdrawal.request` (state machine: requested→approved→paid) and a
   `transfer` variant. *Decision: add now or in the financial step?*
2. **Notifications / broadcast** — `POST /admin/notifications/broadcast` and FCM
   delivery (`alk_device_token_fcm` exists) have no log model. Recommend
   `alkathiry.notification`.
3. **Family graph** — delegation references family but there is no explicit
   household/family entity. Decide between reusing OpenSPP group membership or a
   light `alkathiry.family`.
4. **FR-AVL / FR-CMP / FR-SCL** — meanings unconfirmed (Arabic). May require new
   entities (e.g. a complaints/grievance table). Need confirmation.
5. **UC-02…07 titles** — inferred, not read. Please confirm ordering.

---

## 9. What is genuinely working vs. modelled-only

- **Working at the DB level:** immutability triggers on `transaction` and
  `audit.log`; all indexes; uniqueness constraints; the full dynamic schema is
  installable.
- **✅ Step 2 implemented (verification engine):** dynamic state machine reading
  the pipeline from `verification.stage.config` (+category override); approve /
  reject / escalate transitions; BR-VER-03 auto-escalation after X consecutive
  rejections; FR-VER-05 scope matching via the `geo.area` tree; quorum policy;
  hourly SLA cron (reminder at T, auto-escalate at T+escalation); audit logging;
  **admin UI** (menus, list/form/search, status bar + action buttons) and a
  **Settings panel** for the governance/timing parameters.
- **✅ Step 3 implemented (distribution validation engine):**
  `alkathiry.distribution.engine` runs the 5-condition matrix (FR-DIS-03 #1–#5)
  with a safe JSON predicate DSL (no eval), reset-window-aware quota accounting,
  and a structured verdict; the nightly `_cron_reset_balances` zeroes daily/
  periodic balances per balance-type policy (logging `reset_loss` movements) while
  preserving structural allocations.
- **✅ Step 4 implemented (API gateway + redemption loop + Flutter foundation):**
  `alkathiry.token.service` issues/verifies barcode JWT, redemption OTP and session
  JWT (HS256, mirrored by `identity.token` for revocation). REST controllers under
  `/api/v1` cover OTP login, registration metadata, beneficiary services/barcode,
  and the distributor `scan → OTP → confirm` loop (26.1), posting an immutable
  double-entry redemption with commission split + stock decrement. A dependency-light
  Flutter client (`mobile_app/`) renders registration/home/distributor screens
  reflectively from the JSON payloads.
- **Still modelled but not yet behaving:** commission *reporting*, certificate
  rendering, ad serving (Step 5).
- **Partially / hardening needed:** full OAuth2 flow (current login is phone+OTP →
  session JWT), live camera scanning + offline queue on the Flutter side.

Next recommended step: **Step 5 — native Odoo financial reports (§23.5.3) and the
ad-serving endpoint**.
