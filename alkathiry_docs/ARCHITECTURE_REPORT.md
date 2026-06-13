# التقرير المعماري وخطة إعادة الهيكلة — منصة قبيلة الكثيري الرقمية

> وثيقة تخطيط فقط. لا تتضمن كوداً تنفيذياً. مديول `alkathiry_project` السابق **مجمّد** ولن يُعدّل.
> القرار الأساسي: **نبني فوق OpenSPP بالوراثة، لا من الصفر.**

---

## 0. سجل القرارات المعمارية (ADR)

| # | القرار | الخيار المعتمد | الأثر |
|---|--------|----------------|-------|
| 1 | الهيكلة القبلية | **group-of-groups** عبر `spp_registry_group_hierarchy` | لا نموذج شجري مخصّص |
| 2 | خط التحقق/الاعتماد الهرمي | **`spp_approval`** متعدّد المراحل | يُلغى محرّك `verification.request` اليدوي |
| 3 | توزيع الخدمات بالحصص | **`spp_programs`** + امتداد `quota`/`is_redeemed` | يُلغى محرّك service/wallet/transaction اليدوي |
| 4 | المخرج الحالي | **تقرير فقط** (بدون كود) | تنفيذ مرحلي بعد الاعتماد |

---

## 1. ملخص المشروع والهدف والنتائج المتوقعة

### 1.1 المشروع
منصة رقمية لقبيلة الكثيري تُبنى كطبقة وراثة رقيقة (`alkathiry_*`) فوق منظومة **OpenSPP** الموجودة في هذا الـ repo، وتركّز على ثلاثة محاور: **تسجيل البيانات**، **الهيكليات الديناميكية**، **توزيع الخدمات والبرامج**.

### 1.2 الهدف
تمكين اللجنة المركزية من بناء وتعديل — **من الواجهات ودون كود** — الهيكلة القبلية وهيكلة المناطق وهيكلة الخدمات، وربط المستخدمين بنطاقاتهم، وإطلاق برامج توزيع بحصص ومنع ازدواج الصرف.

### 1.3 النتائج المتوقعة
1. سجلّ ديناميكي للأفراد والمجموعات مع معرّفات وعلاقات.
2. هيكلة قبلية ومناطقية متعددة المستويات قابلة للتعديل من الواجهة.
3. أدوار مستخدمين مقيّدة بالنطاق الجغرافي/القبلي (عاقل/شيخ/موزّع).
4. خط اعتماد هرمي قابل للضبط (مراحل، SLA، تصعيد).
5. برامج توزيع خدمات (نقدية وعينية) بحصص ونقاط صرف تمنع الازدواج.
6. كل ذلك مبني على وحدات OpenSPP المستقرة (production) → كود أقل، متانة أعلى.

### 1.4 المهمة الحالية
**اعتماد هذا التقرير والخطة** قبل كتابة أي كود. لا يُنشأ أي مديول قبل موافقتك على الخطة.

---

## 2. خريطة الوراثة: لكل متطلب → المديول المُورَّث → ما نضيفه

| المتطلب | يُورَّث من | الموديل/الحقل المحوري | الإضافة المطلوبة (رقيقة) |
|---------|-----------|----------------------|--------------------------|
| تسجيل أفراد/مجموعات | `spp_registry` | `res.partner` (is_registrant/is_group)، `spp.group.membership`، `spp.registry.id`، `spp.registry.relationship` | لا شيء جوهري |
| الديناميكية (قوائم/فئات) | `spp_vocabulary` | `spp.vocabulary` + `spp.vocabulary.code` (`namespace_uri`, `parent_id`, `is_hierarchical`) | تعريف vocabularies للقبيلة/المناطق/الخدمات |
| حقول مخصّصة للمسجّل | `spp_custom_field` | `spp.custom.field.group` + `ir.model.fields` | مجموعات حقول قبلية |
| تعبيرات الأهلية/التهديف | `spp_cel_domain` | `spp.cel.expression` / `spp.cel.variable` / concept groups | متغيّرات/تعبيرات قبلية |
| الهيكلة القبلية | `spp_registry_group_hierarchy` | group-of-groups عبر `spp.group.membership` + `allow_all_member_type` على نوع المجموعة | أنواع مجموعات (حي/قبيلة/كبرى/اتحاد) كأكواد vocabulary + قيود مستوى |
| هيكلة المناطق | `spp_area` | `spp.area` (`_parent_store`, `parent_path`, `area_level`) + `spp.area.type` | تعريف area types (إقليم/مديرية/حي) |
| إحداثيات جغرافية | `spp_registrant_gis` / `spp_gis` | `res.partner.coordinates`، `spp.area.geo_polygon` | اختياري |
| نقاط الصرف/الموزّعون | `spp_service_points` | `spp.service.point` (`area_id`, `service_type_ids`, شركة) | ربط بالموزّع |
| ربط المستخدم بالنطاق | `spp_user_roles` + `spp_area` | `res.users.role` (`role_type`), `role.line.local_area_ids`, `res.users.center_area_ids`, ir.rule `area_id child_of` | امتداد النطاق ليشمل عُقد القبيلة |
| الصلاحيات | `spp_security` | مجموعات/فئات/قواعد OpenSPP | مجموعات قبلية (عاقل/شيخ…) |
| خط الاعتماد الهرمي | `spp_approval` | `spp.approval.definition` + `spp.approval.tier` + `spp.approval.mixin` | تعريف خط التسجيل القبلي |
| البرامج وتوزيع الخدمات | `spp_programs` | `spp.program` + managers + `spp.cycle` + `spp.entitlement(.inkind)` + `spp.payment` | امتداد حصص + منع ازدواج |
| الأهلية بالتهديف (PMT) | `spp_scoring_programs` | `scoring_model_id`, `eligibility_min/max_score` | نموذج تهديف قبلي |

---

## 3. التصميم التفصيلي لكل محور

### 3.1 أساس الديناميكية — Vocabularies (المفتاح)
- كل قائمة ديناميكية = `spp.vocabulary.code` ضمن `namespace_uri`. المستخدم يضيف كوداً من الواجهة، وكل حقل `Many2one("spp.vocabulary.code")` يلتقطه فوراً.
- vocabularies التي سننشئها:
  - `urn:alkathiry:vocab:tribe-level` (هيكلي: حي → قبيلة → قبيلة كبرى → اتحاد) — يُسقط على **أنواع المجموعات**.
  - `urn:alkathiry:vocab:service-category` (فئات الخدمات).
  - أنواع المناطق عبر `spp.area.type` (إقليم/مديرية/حي).
- **concept groups** + **CEL** للاستهداف الدلالي (`is_priority_tribe`, `is_low_income`) دون كود.

### 3.2 تسجيل البيانات — Registry
- الفرد والمجموعة كلاهما `res.partner` (`is_registrant=True`، `is_group`).
- المعرّفات (وطني/وظيفي) عبر `spp.registry.id` بأنواع vocabulary (يحلّ مكان `national_id` اليدوي + يضاف `spp_encryption` للتشفير).
- العلاقات (عائلة/تفويض) عبر `spp.registry.relationship` (يحلّ ثغرة العائلة/التفويض).

### 3.3 الهيكلة القبلية — group-of-groups (القرار 1)
- نمط: المجموعة الأب تحتوي مجموعة ابن عبر `spp.group.membership` (`group`=الأب، `individual`=الابن) مع تفعيل `allow_all_member_type=True` على نوع المجموعة في الـ vocabulary.
- مثال: حي «السلام» (group) ← عضوية ← قبيلة «بني هلال» (group) ← عضوية ← فرد.
- **المستخدم من الواجهة**: يضيف/يعدّل أنواع المستويات (أكواد vocabulary) ويبني العُقد ويُسند الأفراد — دون كود.
- إضافة رقيقة مقترحة: نموذج خفيف `alkathiry.tribe.level` (sequence + group_type_id + parent_level_id) لفرض ترتيب المستويات والتحقق منه فقط (اختياري).
- استعلام النسب: عبر `spp.group.membership` تصاعدياً (لا `parent_id` على الشريك).

### 3.4 هيكلة المناطق — spp_area
- `spp.area` شجرة كاملة جاهزة؛ `spp.area.type` يعرّف المستويات. المستخدم يضيف الأقاليم/المديريات/الأحياء من الواجهة ويعدّلها.
- المسجّل يرتبط بـ `res.partner.area_id`.

### 3.5 ربط المستخدمين بالنطاق (القرار ضمن user_roles)
- الدور `res.users.role` بـ `role_type=local/global`؛ سطر الدور `role.line.local_area_ids` يقيّده بمناطق.
- `res.users.center_area_ids` (محسوب) + **ir.rule** `area_id child_of center_area_ids` ⇒ المستخدم المحلي يرى فقط نطاقه وفروعه. مستخدم واحد = عدة أدوار/نطاقات (يحقق FR-VER-05 جاهزاً).
- امتداد رقيق: إضافة `local_tribe_ids` على سطر الدور لربط الأدوار بعُقد القبيلة (مثل المناطق تماماً)، وقاعدة ir.rule مماثلة على عضوية المجموعة.

### 3.6 خط الاعتماد الهرمي — spp_approval (القرار 2)
- `spp.approval.definition` (use_multitier=True) + `spp.approval.tier` لكل مرحلة (عاقل/شيخ/شيخ كبير/لجنة) مع: `approval_type` (group/user/field/manager)، `min_approvers`، `is_blocking`، `sla_hours`، تصعيد.
- نُدخل `spp.approval.mixin` على نموذج طلب التسجيل (أو على `change_request` إن استخدمناه) ⇒ نحصل على `action_submit_for_approval/approve/reject` وSLA جاهزة.
- التصعيد عند الرفض/تجاوز SLA مضبوط من الواجهة (يحلّ محل BR-VER-03 اليدوي).

### 3.7 توزيع الخدمات بالحصص — spp_programs + امتداد (القرار 3)
- التدفق الجاهز: `spp.program` → managers (eligibility/dedup/entitlement/payment) → `spp.cycle` → `spp.entitlement(.inkind)` → صرف عند `spp.service.point`.
- الاستهداف بالفئة/المنطقة/القبيلة: عبر `eligibility_domain` أو **CEL** أو `admin_area_ids` (جاهز).
- **امتداد الحصص ومنع الازدواج (الإضافة الوحيدة الجوهرية):**
  - نموذج جديد `alkathiry.allocation.quota` (program/cycle/category_code/total_quota/used_quota/available_quota).
  - وراثة `spp.program.entitlement.manager.cash/inkind` وتعديل `prepare_entitlements()` لاحترام الحصة لكل فئة/منطقة/قبيلة.
  - وراثة `spp.entitlement` بإضافة `is_redeemed` + `redemption_service_point_id` + `redeem_entitlement()` ⇒ **منع ازدواج الصرف** عند نقطة الخدمة.
- التهديف (PMT): تفعيل `spp_scoring_programs` (min/max score، تصنيفات) عند الحاجة.

---

## 4. المديولات الجديدة المقترحة (طبقات رقيقة)

| المديول | يعتمد على | المحتوى |
|---------|-----------|---------|
| `alkathiry_base` | spp_registry, spp_vocabulary, spp_security | vocabularies القبيلة/الخدمات، مجموعات صلاحيات، قائمة جذر |
| `alkathiry_tribe` | spp_registry_group_hierarchy, alkathiry_base | أنواع مستويات القبيلة + قيود + واجهات |
| `alkathiry_geo` | spp_area, spp_registrant_gis | area types + ربط المسجّلين + واجهات |
| `alkathiry_roles` | spp_user_roles, spp_area, alkathiry_tribe | أدوار قبلية + نطاق قبلي + قواعد ir.rule |
| `alkathiry_approval` | spp_approval, alkathiry_roles | تعريف خط الاعتماد + mixin على التسجيل |
| `alkathiry_services` | spp_programs, spp_service_points, spp_scoring_programs | امتداد الحصص + منع الازدواج + واجهات |
| `alkathiry_dynamics` | spp_cel_*, spp_custom_field | متغيّرات/تعبيرات/حقول مخصّصة |

---

## 5. ما يُسحب من `alkathiry_project` المجمّد

| ما بُني يدوياً | البديل المعتمد |
|----------------|----------------|
| `res.partner` ext + geo.area + national_id | spp_registry + spp_area + reg_id + spp_encryption |
| verification.stage.config + verification.request (محرّك الحالة) | spp_approval (tiers) |
| service + service.allocation + wallet + transaction + distribution.engine | spp_programs (entitlements) + امتداد quota/is_redeemed |
| token_service / controllers | spp_oauth + spp_api_v2 (لاحقاً عند طبقة API) |
| audit.log + trigger | spp_audit (مع إمكانية إبقاء trigger الحصانة) |
| ad.campaign / financial_report | يُعاد تقييمها لاحقاً (خارج المحاور الثلاثة الحالية) |

> لا يُحذف شيء الآن؛ يبقى مجمّداً كمرجع حتى تكتمل النسخة المبنية على spp.

---

## 6. الخطة المرحلية التنفيذية (بعد الاعتماد)

| مرحلة | المخرج | معيار القبول |
|------|--------|---------------|
| **P0** | اعتماد هذا التقرير | موافقتك المكتوبة |
| **P1** | `alkathiry_base` (التبعيات + vocabularies + قائمة) | تثبيت ناجح + ظهور القوائم الديناميكية |
| **P2** | `alkathiry_tribe` (هيكلة قبلية group-of-groups + واجهات) | إنشاء حي/قبيلة وإسناد أفراد من الواجهة |
| **P3** | `alkathiry_geo` (مناطق + ربط المسجّلين) | بناء شجرة مناطق وربط مسجّل |
| **P4** | `alkathiry_roles` (أدوار + نطاق + ir.rule) | مستخدم محلي يرى نطاقه فقط |
| **P5** | `alkathiry_approval` (خط الاعتماد الهرمي) | طلب تسجيل يمرّ عاقل→شيخ→لجنة + تصعيد |
| **P6** | `alkathiry_services` (برامج + حصص + منع ازدواج) | توزيع بحصة لكل قبيلة ومنع صرف مكرّر |
| **P7** | `alkathiry_dynamics` (CEL/حقول مخصّصة) + تقارير | استهداف عبر CEL + حقول مضافة من الواجهة |

كل مرحلة: كود + تحقق ثابت (compile/ruff/xml) + (عند الإمكان) تنصيب حيّ عبر docker-compose.

---

## 7. المخاطر والتخفيف

| الخطر | التخفيف |
|-------|---------|
| اقتران قوي بـ OpenSPP | إبقاء الإضافات رقيقة وفي مديولات `alkathiry_*` منفصلة |
| استعلام نسب القبيلة (لا closure table) | إضافة فهرسة/جدول إغلاق عند ظهور بطء |
| فجوات لغوية في الـ PRD (عربي) | تثبيت المصطلحات معك قبل كل مرحلة |
| تعارض إصدارات Odoo 19 | الالتزام بأنماط الـ repo (`<list>`, managers, mixins) |
| فقدان ميزات بنيتها (immutable ledger) | دمجها كطبقة فوق spp_audit إن لزم |

---

## 8. أسئلة مفتوحة (للمرحلة القادمة)
1. هل الموزّع = `spp.service.point` (شركة + منطقة) أم كيان مستقل؟ (مبدئياً: service point).
2. هل التسجيل يُدار عبر `spp_change_request_v2` (تعديلات بموافقة) أم نموذج تسجيل مباشر + approval mixin؟
3. هل نفعّل التهديف (PMT) في الإطلاق الأول أم لاحقاً؟
4. هل نحتاج API للموبايل في هذه المرحلة (spp_api_v2) أم لاحقاً؟

---

**الحالة:** بانتظار اعتماد الخطة لبدء المرحلة P1، أو تعديل أي بند قبل الاعتماد.
