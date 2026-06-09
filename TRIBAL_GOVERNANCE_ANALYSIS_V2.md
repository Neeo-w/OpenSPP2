# تحليل معماري مصحح: OpenSPP → منصة حوكمة اجتماعية وقبلية
**الإصدار:** 2.0 — مبني على فحص كامل للكود الفعلي (حقول + ميثودز + نماذج)
**التاريخ:** يونيو 2026

---

## تنبيه منهجي

التحليل الأول (v1.0) أخطأ في ثلاثة أوجه:
1. اقترح بناء موديولات جديدة لوظائف **موجودة بالفعل** في الكود
2. لم يفحص الحقول الفعلية على `res.partner` ولا نماذج كاملة كـ`spp_session_tracking`
3. قدّر جهد التطوير الجديد بـ35% وهو في الحقيقة **أقل من 15%**

هذا التحليل مبني على قراءة كل ملف Python في 40+ موديول.

---

## 1. ما يوجد فعلاً في النظام (مفاجآت الفحص العميق)

### 1.1 حقول موجودة على `res.partner` لم تُذكر في v1

| الحقل | النوع | الدلالة القبلية |
|---|---|---|
| `occupation_id` | Many2one → `spp.vocabulary.code` (ILO ISCO-08) | سجل المهنيين **موجود بالفعل** |
| `civil_status_id` | Many2one → vocabulary (UN Marital Status) | الحالة الاجتماعية موجودة |
| `income` | Float | الدخل موجود |
| `tags_ids` | Many2many → vocabulary (registrant-tags) | تصنيفات مرنة موجودة |
| `registration_date` | Date (indexed) | تاريخ التسجيل موجود |
| `related_1_ids` / `related_2_ids` | One2many → `spp.registry.relationship` | علاقات النسب موجودة |
| `area_id` | Many2one → `spp.area` | منطقة الإقامة موجودة (من `spp_area`) |
| `disabled` + `disabled_reason` + `disabled_by` | Datetime + Text + M2O | إلغاء تفعيل ناعم موجود |
| `reg_ids` | One2many → `spp.registry.id` | أرقام هوية متعددة موجودة |
| `company_id` | Many2one → `res.company` | متعدد المؤسسات موجود |

**المعنى العملي:** سجل المهنيين والروابط المهنية يُبنى بـ**إضافة بيانات vocabulary** فقط — لا كود جديد.

---

### 1.2 موديول `spp_session_tracking` يغطي "المجالس" كاملاً

الفحص العميق كشف موديولاً مكتملاً تماماً لم يُذكر في v1:

**`spp.session`** يحتوي على:
```
name, session_type_id (Many2one → spp.session.type)
date, start_time, end_time, duration_hours (computed)
facilitator_id (Many2one → res.users)  ← رئيس الجلسة
co_facilitator_ids (Many2many → res.users)  ← نواب الرئيس
location (Char), area_id (Many2one → spp.area)
track_topics (Boolean, related)
topic_ids (Many2many → spp.session.topic)
expected_participant_ids (Many2many → res.partner)
attendance_ids (One2many → spp.session.attendance)
attendance_count, attendance_rate (computed)
state: scheduled → in_progress → completed/cancelled
notes (Text)
```

**`spp.session.type`** يحتوي على:
```
name, code, frequency (weekly/biweekly/monthly/quarterly/one_time)
required_attendance_percentage
duration_hours
track_topics → topic_ids (One2many → spp.session.topic)
```

**`spp.session.attendance`** يحتوي على:
```
session_id, participant_id (res.partner)
is_attended (Boolean), attendance_time
is_excused, excuse_reason
```

**الخلاصة:** المجالس والجلسات وحضور الأعضاء **مغطاة 100%** — يكفي:
- إضافة أنواع جلسات: "مجلس عام"، "جلسة طارئة"، "اجتماع لجنة"
- إضافة حقل `resolution_ids` (قرارات الجلسة) = ONE2MANY بسيط

---

### 1.3 موديول `spp.registry.relationship` يغطي شجرة النسب (البيانات)

```python
source (Many2one → res.partner, domain: is_registrant=True)
destination (Many2one → res.partner, domain: is_registrant=True)
relation_id (Many2one → spp.vocabulary.code)
available_relation_ids  # يُحسب تلقائياً بناءً على نوع المصدر والهدف
  # Individual↔Individual → concept_group: group_rel_individual_to_individual
  # Group↔Group → concept_group: group_rel_group_to_group
  # Mixed → concept_group: group_rel_mixed
disabled (Datetime), start_date, end_date
```

كل علاقات النسب (أب/أم/ابن/أخ/جد...) تُضاف كـ**vocabulary codes** في:
`urn:openspp:vocab:relationship` → concept group: `group_rel_individual_to_individual`

الفجوة الوحيدة: **عرض الشجرة المرئية** (D3.js/OrgChart) — البيانات موجودة، الواجهة غائبة.

---

### 1.4 موديول `spp.group.membership` يغطي المناصب القيادية

```python
group (Many2one → res.partner)
individual (Many2one → res.partner)
membership_type_ids (Many2many → spp.vocabulary.code, domain: group-membership-type)
start_date (Datetime, default now)
ended_date (Datetime)
status: active/inactive  ← محسوب تلقائياً من ended_date
is_ended (Boolean)
```

المناصب (شيخ، عاقل، عدل، أمين...) تُضاف كـ**vocabulary codes** في:
`urn:openspp:vocab:group-membership-type`

الفجوة: حقلان فقط غائبان:
- `appointment_method`: منتخب/معيَّن/موروث/بالتوافق
- `is_primary_membership`: تمييز الانتماء الأساسي من الثانوي

---

### 1.5 موديول `spp.approval` يغطي سير التوثيق الكامل

```python
# ApprovalDefinition
model_id, approval_type (group/user/manager/field)
use_multitier → tier_ids (One2many → spp.approval.tier)
domain (CEL/Odoo domain للتطبيق الشرطي)
is_emergency_bypass_allowed, sla_days, escalation_definition_id

# ApprovalTier
sequence, approval_type, approval_group_id
is_require_all (ALL مطلوبون أم واحد يكفي)
min_approvers, can_self_approve
sla_hours, is_blocking
```

سير عمل توثيق الانتماء يُبنى **من الإعدادات** مباشرة:
```
Tier 1 (seq=10): مجموعة "العقلاء"       → any approver sufficient
Tier 2 (seq=20): مجموعة "مشائخ الأفخاذ" → 1 approver minimum
Tier 3 (seq=30): مجموعة "شيخ القبيلة"   → require_all=True
Tier 4 (seq=40): مجموعة "لجنة الاعتماد" → min_approvers=3
```

---

### 1.6 موديول `spp.case` يغطي النزاعات والوساطة

```python
# spp.case
case_type_id (Many2one → spp.case.type)
client_type: individual/household/group
partner_id (المشتكي/الطرف الأول)
stage_id (workflow stages ديناميكية)
intake_source: walk_in/referral/outreach/grm/program/other
risk_factor_ids, vulnerability_ids
assessment_ids, intervention_plan_ids, visit_ids, referral_ids
closure_outcome: goals_achieved/partial/disengaged/transferred/...
priority, severity (low/medium/high/critical)
```

النزاعات القبلية تُمثَّل بـ**أنواع حالات جديدة**:
- `case_type`: "نزاع أرض"، "نزاع ميراث"، "جريمة شرف"، "وساطة"
- `stage`: "قيد الدراسة" → "جلسة صلح" → "حكم" → "تنفيذ"

لا موديول جديد مطلوب — فقط بيانات تهيئة.

---

### 1.7 موديول `spp_land_record` يغطي الأملاك والأوقاف جزئياً

```python
# spp.land.record
land_farm_id (Many2one → res.partner)  ← المالك
owner_id (Many2one → res.partner)
lessee_id (Many2one → res.partner)
lease_start, lease_end (Date)
land_use_id (Many2one → vocabulary: urn:openspp:vocab:land-use)
land_coordinates (GeoPointField)
land_geo_polygon (GeoPolygonField)
land_acreage (Float)
```

الأملاك القبلية والوقفية يمكن تمثيلها بـ**إضافة vocabulary codes** لـ`land_use`:
- "وقف ذري"، "وقف خيري"، "ملك قبيلة"، "أرض مشاع"

الفجوة: حقول مالية (قيمة الأصل، الإيراد السنوي، المستفيدون) → تحتاج موديول وقف.

---

### 1.8 موديول `spp_scoring` يغطي أهلية الخدمات بالكامل

```python
# spp.scoring.model
calculation_method: weighted_sum/cel_formula/lookup_table/external/custom
cel_expression (Text)  ← قاعدة CEL قابلة للتكوين
category: poverty/vulnerability/eligibility/triage/custom
threshold_ids (One2many → spp.scoring.threshold)
```

أهلية الخدمات المجتمعية تُعرَّف كـ**نماذج تسجيل** من الإعدادات:
- نموذج: "أهلية المنحة الدراسية" → CEL: `r.income < 5000 AND r.age < 25`
- نموذج: "أهلية دعم الزواج" → CEL: `r.civil_status == "single" AND r.age > 18`

---

## 2. جدول إعادة الاستخدام المصحح (مستوى الحقول)

### 2.1 يُستخدم مباشرة — صفر كود جديد

| الموديول/النموذج | الاستخدام في المنصة | ما يُضاف |
|---|---|---|
| `spp_registry` + `res.partner` | سجل الأفراد والكيانات بجميع مستوياتها | vocabulary entries فقط |
| `spp_registry_group_hierarchy` | الهيكل الهرمي (اتحاد→فرد) | تفعيل `allow_all_member_type` |
| `spp.group.membership` | عضوية + مناصب قيادية | 2 حقول فقط |
| `spp.registry.relationship` | علاقات النسب الكاملة | vocabulary codes فقط |
| `spp_vocabulary` | كل التصنيفات الديناميكية | إضافة namespaces جديدة |
| `spp_approval` (multi-tier) | توثيق الانتماء والتعيينات | إعداد من UI |
| `spp_change_request_v2` | طلبات انتماء وتغيير | قوالب CR جديدة |
| `spp_session_tracking` | **المجالس والجلسات** — مكتمل | نوع جلسة + حقل قرارات |
| `spp_area` + `spp_gis` | الجغرافيا حتى 10 مستويات | area types جديدة |
| `spp_case_base` | النزاعات والوساطة القبلية | أنواع حالات + stages |
| `spp_grm` | التظلمات والشكاوى | تصنيفات جديدة + stages |
| `spp_programs` + `spp_scoring` + CEL | كل الخدمات المجتمعية | program types + CEL rules |
| `spp_dms` | وثائق العضوية والعقود | document types |
| `spp_audit` | سجل تدقيق كامل | audit rules |
| `spp_event_data` | أحداث القبيلة والقرارات | event types |
| `spp_consent` | موافقات اشتراك البيانات | consent types |
| `spp_land_record` | الأملاك القبلية والتاريخية | land_use vocabulary |
| `spp_encryption` + `spp_key_management` | حماية بيانات النسب الحساسة | مباشرة |
| `spp_analytics` + `spp_indicator` + Studio | إحصائيات وتقارير ديناميكية | مؤشرات جديدة |
| `spp_api_v2` | REST API للتطبيق المحمول | مباشرة |
| `spp_user_roles` + `spp_security` | صلاحيات حسب المنصب والمنطقة | أدوار جديدة |
| `spp_banking` | حسابات صناديق التكافل | مباشرة |
| `spp_service_points` | نقاط خدمة مجتمعية | service_type vocabulary |

**إجمالي: ~22 موديولاً يُستخدم مباشرة أو بإضافة بيانات فقط**

---

### 2.2 يحتاج إضافة حقول بسيطة — جهد < أسبوع لكل

| النموذج | الحقول المضافة | السبب |
|---|---|---|
| `spp.group.membership` | `appointment_method` (Selection: elected/appointed/inherited/consensus)، `is_primary_membership` (Boolean) | تمييز المنصب المنتخب من المعيَّن + الانتماء الأساسي |
| `res.partner` (عبر موديول جديد `spp_area`) | `area_origin_id` (Many2one → spp.area "منطقة الأصل")، `area_work_id` (Many2one → spp.area "منطقة العمل") | حالياً `area_id` واحدة فقط |
| `spp.session` | `resolution_ids` (One2many → `spp.session.resolution` جديد بسيط)، `group_id` (Many2one → res.partner "الجهة المنظِّمة") | ربط القرارات بالجلسة + الجهة المستضيفة |
| `spp.land.record` | `asset_value` (Float "قيمة الأصل")، `annual_revenue` (Float)، `waqf_type` (Selection: dhuri/khairi/tribal) | تمييز الوقف عن الملك العادي |

---

### 2.3 يحتاج تطوير متوسط — موديولات صغيرة جديدة حقيقية

#### أ. `spp_tribal_registry` — موديول تهيئة فقط (ليس نماذج جديدة)

**الغرض:** حزمة تهيئة تُثبَّت مرة واحدة تُضيف:
- **vocabulary data**: أنواع المجموعات، أنواع العلاقات، أنواع المناصب، تصنيفات الخدمات
- **ir.sequence**: أرقام قيد تلقائية لكل مستوى هرمي
- **approval.definition templates**: قوالب سير عمل الانتماء والتوثيق
- **cr.type templates**: قوالب طلبات الانتماء والنقل والطعن
- **session.type templates**: مجلس عام، جلسة طارئة، اجتماع لجنة
- **case.type templates**: نزاع أرض، وساطة، ميراث
- **audit.rule templates**: قواعد تدقيق مناسبة للسياق القبلي
- **report templates**: شهادة عضوية PDF

**الكود الفعلي:** XML data files فقط، Python بسيط لـ`ir.sequence` — أسبوع واحد للمطور.

#### ب. `spp_genealogy_widget` — واجهة شجرة النسب (Frontend فقط)

**الغرض:** عرض `spp.registry.relationship` في شجرة مرئية تفاعلية.
- البيانات موجودة في النظام → فقط widget جديد
- مكتبة JavaScript: D3.js أو OrgChart.js
- عرض: أب → أبناء → أحفاد بالنقر التفاعلي
- يفتح بطاقة الفرد بالضغط على العقدة
- **ليس نموذج Python جديد** — فقط JS widget + XML view

**الجهد:** 3-4 أسابيع (مطور frontend).

#### ج. `spp_waqf` — الوقف والتبرعات (موديول حقيقي صغير)

يعتمد على `spp_land_record` (الأصول) + `account` (المحاسبة) + `spp_programs` (التوزيع):

```python
class SppWaqf(models.Model):
    _name = "spp.waqf"
    # الربط بالأصل الموجود
    land_record_ids (One2many → spp.land.record)  ← أصول عقارية
    monetary_amount (Float)                          ← أصل نقدي
    waqf_type (Selection: dhuri/khairi/tribal)
    grantor_id (Many2one → res.partner)              ← الواقف
    beneficiary_group_id (Many2one → res.partner)    ← المجموعة المستفيدة
    waqf_deed_id (Many2one → spp.dms.file)          ← صك الوقف
    established_date (Date)
    annual_revenue (Float)
    linked_program_id (Many2one → spp.program)       ← صندوق توزيع
    state (Selection: active/frozen/disputed/ended)
    # Contribution/Donation tracking
    donation_ids (One2many → spp.waqf.donation)

class SppWaqfDonation(models.Model):
    _name = "spp.waqf.donation"
    waqf_id (Many2one → spp.waqf)
    donor_id (Many2one → res.partner)
    donation_type (Selection: cash/in_kind/land)
    amount (Float), donation_date (Date)
    document_id (Many2one → spp.dms.file)
```

**الجهد:** 3-4 أسابيع.

---

### 2.4 يحتاج تطوير جديد حقيقي — موديول `spp_elections`

لا يوجد في OpenSPP أي آلية تصويت أو ترشيح. هذا هو الموديول الوحيد الذي يحتاج بناءً من الصفر.

```python
class SppElection(models.Model):
    _name = "spp.election"
    _inherit: ["mail.thread", "spp.approval.mixin"]
    name, election_type (Selection: council/sheikh/representative/committee)
    electoral_unit_id (Many2one → res.partner, domain: is_group=True)  ← الدائرة
    position_id (Many2one → spp.vocabulary.code)  ← المنصب المنتخب
    election_date (Date), registration_deadline (Date)
    eligibility_expression (Text, CEL)  ← شرط أهلية الناخب
    candidate_eligibility_expression (Text, CEL)
    state: draft → registration → voting → counting → certified
    candidate_ids (One2many → spp.election.candidate)
    ballot_ids (One2many → spp.election.ballot)  ← مشفرة

class SppElectionCandidate(models.Model):
    _name = "spp.election.candidate"
    election_id, partner_id (Many2one → res.partner)
    nomination_source (Selection: self/council/group)
    nominator_id (Many2one → res.partner)
    state: pending → approved/rejected
    vote_count (Integer, computed, protected until certified)

class SppElectionBallot(models.Model):
    _name = "spp.election.ballot"
    election_id, voter_id (Many2one → res.partner)
    voted_for_id (Many2one → spp.election.candidate)
    vote_datetime (Datetime), is_counted (Boolean)
    # لا يُكشف عن الاقتران voter↔voted_for حتى بعد الفرز
```

**الجهد:** 6-8 أسابيع.

---

## 3. تحليل الفجوات المصحح

| # | الفجوة | الحل الصحيح | الجهد الفعلي |
|---|---|---|---|
| 1 | شجرة النسب المرئية | JS widget فقط — البيانات موجودة | 3-4 أسابيع |
| 2 | نظام الانتخابات | موديول `spp_elections` جديد | 6-8 أسابيع |
| 3 | الوقف والتبرعات | موديول `spp_waqf` صغير | 3-4 أسابيع |
| 4 | قرارات الجلسة مرتبطة بالجلسة | حقل `resolution_ids` على `spp.session` | 2-3 أيام |
| 5 | منطقة الأصل ومنطقة العمل | حقلان على `res.partner` | يوم واحد |
| 6 | طريقة التعيين + الانتماء الأساسي | حقلان على `spp.group.membership` | يوم واحد |
| 7 | بيانات التهيئة القبلية | `spp_tribal_registry` (XML فقط) | 1 أسبوع |
| 8 | شهادة العضوية PDF | قالب تقرير Odoo | 2-3 أيام |
| 9 | قيم الوقف على الأصول | 3 حقول على `spp.land.record` | يوم واحد |

**ما أُزيل من قائمة الفجوات في v1 لأنه موجود:**
- ~~سجل المهنيين~~ → `occupation_id` موجود + groups = vocabulary
- ~~المجالس واللجان~~ → `spp_session_tracking` مكتمل
- ~~النزاعات القبلية~~ → `spp_case_base` جاهز بالتهيئة
- ~~التظلمات المجتمعية~~ → `spp_grm` جاهز بالتهيئة
- ~~الخدمات المجتمعية~~ → `spp_programs` + CEL جاهز
- ~~المشاريع المجتمعية~~ → `spp_programs` بنوع "مشروع تنموي"
- ~~الروابط المهنية~~ → groups بـ`group_type = professional_association`
- ~~المغتربون~~ → group + area_origin_id المضاف
- ~~بوابة الأعضاء~~ → Odoo portal موجود في `spp_registry` dependencies
- ~~إدارة الوثائق~~ → `spp_dms` جاهز
- ~~التسلسل الهرمي~~ → `spp_registry_group_hierarchy` + vocabulary جاهز

---

## 4. الخريطة الصحيحة للتحول

### الجهد الحقيقي الموزع

```
┌─────────────────────────────────────────────────────────────────┐
│  إجمالي الجهد المصحح                                           │
│                                                                 │
│  كود Python جديد:     ~15% من الجهد الكلي                      │
│  XML/تهيئة/بيانات:    ~45% من الجهد الكلي                      │
│  JavaScript (widget): ~15% من الجهد الكلي                      │
│  اختبارات وتوثيق:     ~25% من الجهد الكلي                      │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 1: التهيئة والبيانات (6-8 أسابيع)

**كل شيء في هذه المرحلة هو XML بيانات وإعدادات — لا Python جديد**

#### Sprint 1-2: Vocabulary الأساسية (أسبوعان)

**موديول: `spp_tribal_registry` — ملفات data XML فقط**

```xml
<!-- أنواع المجموعات — urn:openspp:vocab:group-type -->
<code="tribal_federation"   display="اتحاد قبلي"  allow_all_member_type="True"/>
<code="tribe"               display="قبيلة"         allow_all_member_type="True"/>
<code="sub_tribe"           display="بطن"           allow_all_member_type="True"/>
<code="clan_branch"         display="فخذ"           allow_all_member_type="True"/>
<code="clan"                display="عشيرة"         allow_all_member_type="True"/>
<code="family"              display="أسرة"          allow_all_member_type="True"/>
<code="council"             display="مجلس"          allow_all_member_type="True"/>
<code="committee"           display="لجنة"          allow_all_member_type="True"/>
<code="professional_assoc"  display="رابطة مهنية"   allow_all_member_type="True"/>
<code="diaspora_org"        display="منظمة مغتربين" allow_all_member_type="True"/>
<code="dhaman_group"        display="مجموعة ضمان"   allow_all_member_type="True"/>

<!-- أنواع العضوية — urn:openspp:vocab:group-membership-type -->
<code="head"                display="رب الأسرة"         is_unique="True"/>
<code="sheikh_al_mashayekh" display="شيخ المشائخ"/>
<code="tribe_sheikh"        display="شيخ قبيلة"/>
<code="sub_tribe_sheikh"    display="شيخ بطن"/>
<code="fakhdh_sheikh"       display="شيخ فخذ"/>
<code="aaqel"               display="عاقل"/>
<code="adl"                 display="عدل"/>
<code="amin"                display="أمين"/>
<code="council_member"      display="عضو مجلس"/>
<code="secretary"           display="كاتب/سكرتير"/>
<code="dhaman_sheikh"       display="شيخ ضمان"/>

<!-- العلاقات — urn:openspp:vocab:relationship (Individual↔Individual) -->
<code="father"   display="أب"/>   <code="mother"  display="أم"/>
<code="son"      display="ابن"/>  <code="daughter" display="ابنة"/>
<code="brother"  display="أخ"/>   <code="sister"  display="أخت"/>
<code="husband"  display="زوج"/>  <code="wife"    display="زوجة"/>
<code="grandfather" display="جد"/> <code="grandmother" display="جدة"/>
<code="uncle"    display="عم/خال"/> <code="aunt"   display="عمة/خالة"/>
<code="cousin"   display="ابن عم/خال"/>
<code="nephew"   display="ابن أخ/أخت"/>

<!-- أنواع المناطق — urn:openspp:vocab:area-type -->
<code="origin_area"    display="منطقة الأصل"/>
<code="residence_area" display="منطقة السكن"/>
<code="work_area"      display="منطقة العمل"/>

<!-- أنواع الجلسات -->
SessionType: "مجلس عام"، "جلسة طارئة"، "اجتماع لجنة"، "جلسة صلح"

<!-- أنواع الحالات -->
CaseType: "نزاع أرض"، "وساطة"، "نزاع ميراث"

<!-- أنواع البرامج/الخدمات -->
ProgramType (via vocabulary): "منحة دراسية"، "مساعدة علاجية"، "دعم زواج"، "صندوق تكافل"
```

#### Sprint 3-4: الحقول البسيطة المضافة (أسبوعان)

**موديول: `spp_tribal_extensions` — Python بسيط جداً**

```python
# 1. إضافة على res.partner (عبر spp_area):
area_origin_id = fields.Many2one("spp.area", "منطقة الأصل")
area_work_id   = fields.Many2one("spp.area", "منطقة العمل")

# 2. إضافة على spp.group.membership:
appointment_method = fields.Selection([
    ('elected',   'منتخب'),
    ('appointed', 'معيَّن'),
    ('inherited', 'موروث'),
    ('consensus', 'بالتوافق'),
], "طريقة التعيين")
is_primary_membership = fields.Boolean("الانتماء الأساسي")

# 3. إضافة على spp.session:
resolution_ids = fields.One2many("spp.session.resolution", "session_id", "القرارات")
organizer_group_id = fields.Many2one("res.partner", "الجهة المنظِّمة",
    domain=[("is_group","=",True),("is_registrant","=",True)])

# نموذج جديد بسيط:
class SppSessionResolution(models.Model):
    _name = "spp.session.resolution"
    _description = "قرار جلسة"
    session_id = fields.Many2one("spp.session", required=True, ondelete="cascade")
    number     = fields.Integer("رقم القرار")
    title      = fields.Char("عنوان القرار", required=True)
    body       = fields.Html("نص القرار")
    vote_for   = fields.Integer("مع")
    vote_against = fields.Integer("ضد")
    vote_abstain = fields.Integer("امتناع")
    state      = fields.Selection([('draft','مسودة'),('passed','مُقرّ'),('rejected','مرفوض')])

# 4. إضافة على spp.land.record (للوقف):
waqf_type    = fields.Selection([
    ('dhuri','وقف ذري'), ('khairi','وقف خيري'), ('tribal','ملك قبيلة')
], "نوع الوقف/الملك")
asset_value  = fields.Float("القيمة التقديرية")
annual_revenue = fields.Float("الإيراد السنوي")
```

**ملاحظة:** هذان الموديولان (`spp_tribal_registry` + `spp_tribal_extensions`) يمثلان **ما قدّرته v1 بـ5 موديولات جديدة**.

#### Sprint 5-6: إعداد سير العمل من الواجهة (أسبوعان)

**لا كود — فقط إعداد من شاشات النظام:**

- تعريف `ApprovalDefinition` متعددة المستويات لكل قبيلة
- تعريف `Change Request Types`: طلب انتماء، طلب نقل، طعن في انتماء
- إعداد GRM stages للتظلمات القبلية
- إعداد Case stages للنزاعات والوساطة
- إعداد Program types للخدمات
- إعداد CEL expressions لشروط الأهلية
- الأدوار والصلاحيات الجغرافية: شيخ قبيلة يرى قبيلته فقط

**مخرجات Phase 1:**
✅ هيكل هرمي كامل (اتحاد → فرد) يعمل
✅ مناصب قيادية مع طريقة التعيين والمدة
✅ علاقات النسب كاملة قابلة للتسجيل
✅ المجالس والجلسات مع القرارات
✅ النزاعات والتظلمات بسير عمل مخصص
✅ الخدمات المجتمعية الأساسية
✅ الصلاحيات الجغرافية للمناصب

---

### Phase 2: الواجهات الجديدة والموديولات الحقيقية (8-10 أسابيع)

#### Sprint 7-9: شجرة النسب المرئية — `spp_genealogy_widget` (3 أسابيع)

**الكود:** JavaScript فقط (Odoo OWL framework)
- يقرأ `spp.registry.relationship` بواسطة RPC
- يعرض شجرة تفاعلية D3.js داخل نموذج الفرد
- Tab جديد "شجرة العائلة" على بطاقة الفرد
- النقر على عقدة يفتح البطاقة
- فلتر العمق (جيل واحد / جيلين / الكل)
- زر "استيراد" من GEDCOM (اختياري)

**لماذا frontend فقط:** بيانات العلاقات في `spp.registry.relationship` كاملة — فقط عرضها بشكل مرئي.

#### Sprint 10-12: موديول الوقف `spp_waqf` (3 أسابيع)

```python
# النماذج المطلوبة فقط (مذكورة في §2.3 أعلاه)
spp.waqf        ← الوقف الرئيسي
spp.waqf.donation ← المساهمات
# التوزيع عبر spp.program الموجود
# الأصول العقارية عبر spp.land.record المحدَّث
# المحاسبة عبر account.move الموجود
```

#### Sprint 13-15: قوالب التقارير والبوابة (أسبوعان)

- شهادة العضوية PDF (Odoo QWeb report)
- وثيقة التعيين في منصب PDF
- محضر جلسة مجلس PDF
- بوابة الأعضاء الذاتية (Odoo Portal المدمج):
  - تقديم طلب انتماء عبر الويب
  - متابعة حالة الطلب
  - عرض بيانات العضو الخاصة

**مخرجات Phase 2:**
✅ شجرة نسب مرئية تفاعلية
✅ نظام وقف وتبرعات متكامل مع المحاسبة
✅ شهادات عضوية ومحاضر جلسات بالنقر
✅ بوابة أعضاء ذاتية عبر الويب

---

### Phase 3: الانتخابات والتحليلات المتقدمة (8-10 أسابيع)

#### Sprint 16-22: موديول الانتخابات `spp_elections` (7 أسابيع)

النموذج الكامل مذكور في §2.3 أعلاه.

**التكاملات:**
- `spp_registry_group_hierarchy` → الدوائر الانتخابية
- CEL engine → شرط أهلية الناخبين والمرشحين
- `spp_approval` → اعتماد نتائج الانتخابات
- `spp_event_data` → تسجيل نتائج رسمية
- `spp_audit` → سجل تدقيق غير قابل للتغيير

#### Sprint 23-25: لوحة الإحصائيات التنفيذية (3 أسابيع)

**عبر `spp_indicator_studio` الموجود — لا كود Python:**

| المؤشر | التعريف في indicator_studio |
|---|---|
| عدد الأفراد لكل قبيلة | COUNT(res.partner) GROUP BY group → group_type = tribe |
| عدد الأسر | COUNT(groups WHERE group_type = family) |
| عدد المشائخ النشطين | COUNT(memberships WHERE type = sheikh AND status = active) |
| توزيع المهن | COUNT(partners) GROUP BY occupation_id |
| المغتربون (خارج منطقة الأصل) | COUNT WHERE area_id != area_origin_id |
| معدل التسجيل السنوي | COUNT(partners) WHERE YEAR(registration_date) = current_year |
| نسبة انجاز الخدمات | SUM(entitlements.delivered) / SUM(entitlements.total) |
| قيمة الوقف | SUM(waqf.asset_value) |

**مخرجات Phase 3:**
✅ انتخابات هرمية إلكترونية كاملة
✅ لوحة إحصاءات تنفيذية ديناميكية
✅ تغطية كاملة لجميع متطلبات المنصة

---

## 5. مقارنة v1 مقابل v2

| البند | التحليل الأول (v1) | التحليل المصحح (v2) |
|---|---|---|
| موديولات جديدة مقترحة | 8 موديولات كاملة | 4 فقط (2 صغيران جداً) |
| الجهد التقديري الكلي | 12-18 شهراً | **6-8 أشهر** |
| سجل المهنيين | موديول جديد مقترح | `occupation_id` موجود — 0 كود |
| المجالس والجلسات | موديول `spp_governance_engine` مقترح | `spp_session_tracking` موجود — 0 كود |
| النزاعات والوساطة | موديول جديد مقترح | `spp_case_base` جاهز — 0 كود |
| التظلمات | مباشر (صحيح في v1) | مباشر |
| الأملاك القبلية | موديول جديد مقترح | `spp_land_record` + 3 حقول |
| منطقة الأصل/العمل | موديول إضافة مقترح | حقلان على `res.partner` — يوم واحد |
| طريقة التعيين | موديول مقترح | حقل واحد على `spp.group.membership` — يوم واحد |
| شهادة العضوية | موديول مقترح | قالب تقرير Odoo — 2-3 أيام |
| الانتخابات | موديول جديد (صحيح) | موديول جديد (صحيح) |
| الوقف | موديول كبير مقترح | موديول صغير + تكامل موجودات |
| شجرة النسب | محرك Python + نماذج جديدة | JS widget فقط — البيانات موجودة |

---

## 6. الخلاصة

**النسبة الحقيقية للإعادة الاستخدام: 85-90%**

الجهد الحقيقي الجديد:
1. `spp_tribal_registry` — XML data فقط (أسبوع)
2. `spp_tribal_extensions` — ~200 سطر Python (أسبوع)
3. `spp_genealogy_widget` — JS widget (3-4 أسابيع)
4. `spp_waqf` — موديول صغير (3-4 أسابيع)
5. `spp_elections` — الموديول الكبير الوحيد الحقيقي (6-8 أسابيع)
6. إعداد vocabulary + تهيئة workflows من الواجهة (3-4 أسابيع)
7. قوالب تقارير + بوابة أعضاء (أسبوعان)

**المجموع: 20-26 أسبوعاً (5-7 أشهر) بدلاً من 12-18 شهراً**

الفرق الجوهري: OpenSPP يملك **بنية تحتية تهيئة قوية جداً** (vocabulary system + CEL engine + approval framework + session tracking + case management) تجعل معظم متطلبات المنصة قابلة للتغطية بـ**بيانات تهيئة** لا بـ**كود جديد**.

---
*تحليل معماري v2.0 — مبني على فحص الكود الفعلي — يونيو 2026*
