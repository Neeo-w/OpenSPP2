# تقرير: تحليل OpenG2P Registry ومقارنته بمشروعنا (OpenSPP2)

> مبني على الكود الفعلي لمستودع `OpenG2P/openg2p-registry` (فرع `develop`، **Odoo 17.0**) مقابل مشروعنا OpenSPP2 (**Odoo 19.0**). المرجع هو الكود المصدري نفسه.

---

## 0. العلاقة بين المشروعين (سياق حاسم)
**OpenSPP (مشروعنا) فرعٌ متطوّر من OpenG2P Registry.** لذا تتشابه الأسماء (`is_registrant`, `is_group`, `group.membership`) لكن مشروعنا **أحدث وأغنى**. النتيجة المبكرة: **لا ننقل كوداً مباشرة** (اختلاف Odoo 17/19 + مشروعنا أحدث) — بل ننقل **المفاهيم والحقول** المفيدة.

---

## 1. تحليل منطق OpenG2P (تسجيل/هرمية/مناطق/مناصب) من الكود

### 1.1 المسجّل — `g2p.registrant` (`g2p_registry_base/models/registrant.py`)
`_inherit = "res.partner"`، أهم الحقول:
- `is_registrant` (Boolean)، `is_group` (Boolean) — **نفس مبدأ مشروعنا**.
- `registration_date` (Date)، `unique_id` (Char، مفهرس فريد) — **معرّف نظام مولّد**.
- `reg_ids` (One2many → `g2p.reg.id`)، `phone_number_ids`، `tags_ids`.
- `related_1_ids` / `related_2_ids` (One2many → `g2p.reg.rel`) — العلاقات الثنائية.
- `civil_status`, `occupation`, `income`.
- **`region` (Many2one → `g2p.region`)** و**`district` (Many2one → `g2p.district`)** — **مباشرة على الشريك**.

### 1.2 المناطق — `g2p.region` (`g2p_registry_base/models/region.py`) ⚠️ نقطة مفصلية
الحقول: `name`, `code`, `iso_code` **فقط**.
- **لا `parent_id`، لا `_parent_store`، لا مستويات/أنواع.**
- أي أن **مناطق OpenG2P مسطّحة (قائمة بسيطة)** + `g2p.district` config منفصل. **لا تدعم شجرة مناطق متعددة المستويات بمسميات مختلفة لكل دولة.**

### 1.3 المجموعة والعضوية (`g2p_registry_membership/models/`)
- `g2p.group.membership`: `group` (domain is_group=True)، `individual` (**domain is_group=False ثابت**)، `kind` (Many2many → `g2p.group.membership.kind`)، `start_date/ended_date/status/is_ended`.
- `g2p.group.membership.kind`: `name` + **`is_unique` (Boolean)** — «نوع عضوية لا يتكرر داخل المجموعة» (مثل رب الأسرة) — **نموذج config مستقل**.
- نوع المجموعة = `kind` (Many2one → `g2p.group.kind`، نموذج مستقل).
- ⚠️ **لا يوجد `allow_all_member_type` ولا مديول `group_hierarchy`** → **OpenG2P Registry لا يدعم «مجموعة داخل مجموعة» (الهرمية متعددة المستويات) جاهزاً.**

### 1.4 المناصب (شيخ/عاقل)
**غير موجودة** — لا في OpenG2P ولا في OpenSPP. إضافة مخصّصة في كلتا الحالتين.

---

## 2. جدول المقارنة المباشر

| البُعد | OpenG2P Registry (17) | مشروعنا OpenSPP2 (19) | الأنسب لنا |
|---|---|---|---|
| فرد/مجموعة | `is_registrant`/`is_group` | نفسه | تعادل |
| **نوع المجموعة** | `g2p.group.kind` (نموذج config) | `group_type_id` → `spp.vocabulary.code` (vocabulary ديناميكي من UI) | **مشروعنا** |
| **نوع العضوية** | `g2p.group.membership.kind` (+`is_unique`) | vocabulary `group-membership-type` | **مزيج** (نقتبس `is_unique`) |
| **هرمية قبيلة⊃عشيرة⊃أسرة** | ❌ غير مدعوم | ✅ `allow_all_member_type` + `spp_registry_group_hierarchy` | **مشروعنا (حاسم)** |
| **المناطق** | `g2p.region` مسطّح + `g2p.district` | `spp.area` شجرة `_parent_store` + `spp.area.type` مستويات | **مشروعنا (حاسم)** |
| ربط المسجّل بالمنطقة | `region`/`district` مباشرة | `area_id` → `spp.area` (شجري) | مشروعنا |
| نطاق المستخدم بالمنطقة | غير ظاهر في base | `local_area_ids` → `center_area_ids` → `ir.rule child_of` | **مشروعنا** |
| العلاقات الثنائية | `g2p.reg.rel` (related_1/2) | `spp.registry.relationship` (source/destination) | تعادل |
| المعرّف الفريد | `unique_id` مولّد + `reg_ids` | `spp.registry.id` (vocabulary id-type) | مزيج (نقتبس `unique_id`) |
| التشفير/الوثائق | `g2p_encryption` + `document_*` | `spp_encryption` + `spp_dms` | تعادل |
| ODK Import / VCI / PMT / Dedup | موديولات جاهزة | جزئي (`spp_dci`, `spp_scoring`) | **نستفيد من OpenG2P** |
| المناصب (شيخ/عاقل) | غير موجود | غير موجود | إضافة مخصّصة |

---

## 3. الخلاصة: كيف نستفيد في مشروعنا

### 3.1 القرار الأساسي
**نبقى على OpenSPP2 كأساس** — فهو **الأنسب حاسماً** لمتطلباتنا الثلاثة الجوهرية:
- الهرمية القبلية متعددة المستويات → موجودة عندنا فقط (`allow_all_member_type`)، **مفقودة في OpenG2P**.
- شجرة المناطق متعددة الدول/المسميات → `spp.area`/`spp.area.type` عندنا، **OpenG2P مسطّح لا يكفي**.
- ربط المستخدمين بالنطاق → `local_area_ids` + `ir.rule` عندنا.

### 3.2 ما نقتبسه من OpenG2P (أفكار/حقول، لا كود)
1. **`is_unique` على نوع العضوية** — أهم اقتباس: في OpenG2P، تفرّد دور داخل المجموعة (رب أسرة واحد) **معطى بيانات قابل للضبط**؛ بينما مشروعنا يثبّت تفرّد "head" في الكود (`group.py:117-120`). نضيف `is_unique` على كود vocabulary `group-membership-type` ليصبح التفرّد ديناميكياً → يخدم «عاقل/رب أسرة واحد لكل أسرة» دون كود.
2. **`unique_id` المولّد على المسجّل** — معرّف نظام فريد للمواطن (مستقل عن أنواع الهوية) — مفيد للباركود والمراجع.
3. **حقل `region`/`district` المباشر** — كاختصار قراءة سريع (محسوب من `area_id`) للحالات البسيطة، مع إبقاء شجرة `spp.area` كمصدر الحقيقة.
4. **موديولات مرجعية للمراحل اللاحقة:**
   - `g2p_odk_importer` — جمع بيانات الميدان (يطابق متطلب CommCare/ODK الأصلي للموزّع/المسجّل).
   - `g2p_openid_vci` (Verifiable Credentials) — إصدار شهادات/هوية رقمية (يطابق فكرة Sunbird RC).
   - `g2p_registry_proxy_means_test` + `deduplicator` — للتهديف ومنع التكرار (يكمّل `spp_scoring`).

### 3.3 ربط بالسيناريوهات المعتمدة
| سيناريو | حكم المقارنة |
|---|---|
| قبيلة ⊃ عشيرة ⊃ أسرة ⊃ أفراد (B1–B6) | OpenG2P **لا يدعمه** → نعتمد group-of-groups في مشروعنا |
| مناطق دول مختلفة بمسميات/أعماق مختلفة (A1–A5) | OpenG2P مسطّح **لا يكفي** → `spp.area` هو الحل |
| تفرّد منصب لكل عقدة (عاقل/رب أسرة) | **نقتبس `is_unique`** من OpenG2P لجعله ديناميكياً |
| المعرّف للباركود | **نقتبس `unique_id`** المولّد |

---

## 4. ماذا لا نأخذ من OpenG2P (وتجنّب التراجع)
- **لا** نأخذ `g2p.region` المسطّح (تراجع عن شجرتنا).
- **لا** نستبدل vocabularies بنماذج `kind` المنفصلة (مشروعنا أكثر ديناميكية).
- **لا** ننقل كوداً بـ Odoo 17 إلى مشروعنا 19 (نقل مفاهيم فقط).

---

**الحالة:** التقرير يثبّت أن **مشروعنا (OpenSPP2) هو الأساس الصحيح**، مع اقتباسات محدّدة من OpenG2P (`is_unique`, `unique_id`, ومراجع ODK/VCI/PMT). تُدمج هذه الاقتباسات في خطة `ARCHITECTURE_REPORT.md` ضمن P2 (`is_unique`) وP1 (`unique_id`) والمراحل المتقدّمة (ODK/VCI/PMT).
