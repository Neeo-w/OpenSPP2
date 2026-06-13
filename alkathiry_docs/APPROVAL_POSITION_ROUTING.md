# مواصفة امتداد التوثيق: توجيه الموثّقين بالمنصب + النطاق (Scoped-Position)

> وثيقة تصميم مبنية على الكود الفعلي لـ `spp_approval`. لا كود تنفيذي هنا — مواصفة للاعتماد.
> كل مرجع كود موثّق بالملف والسطر الحقيقي.

---

## 1. الحقيقة من الكود (الأساس الذي نبني عليه)

### 1.1 نقطة الحلّ الوحيدة للموثّقين
`spp.approval.tier.get_approvers(record)` — `spp_approval/models/approval_tier.py:120-165`.
- يرجع `res.users` recordset.
- يُستدعى من: `action_approve` (`approval_tier_review.py:113`), `_check_tier_completion` (`:165`), `action_reject` (`:189`), `get_current_tier_approvers` (`approval_review_multitier.py:207`).
- **هذه الدالة هي نقطة الامتداد الوحيدة المطلوبة** — لا حاجة لتعديل تدفّق المراحل إطلاقاً.

### 1.2 الأنواع المتاحة حالياً (`approval_type`)
`approval_tier.py:31-41`: `group` / `user` / `manager` / `field`. لا يوجد نوع «منصب مقيّد بنطاق السجل».

### 1.3 النِصاب لكل مرحلة (موجود وجاهز)
`approval_tier.py:63-73` + `approval_tier_review.py:150-177`:
- `is_require_all=False` → تكتمل عند `len(approved_by_ids) >= min_approvers`.
- `is_require_all=True` → تكتمل عند موافقة كل `get_approvers`.
→ «عدد الموثّقين المطلوب لكل مرحلة» مضبوط أصلاً عبر `min_approvers`.

### 1.4 تدفّق المراحل (جاهز — لا نلمسه)
- الإرسال: `spp.approval.mixin.action_submit_for_approval` ينشئ المراجعة.
- `approval_review_multitier._create_tier_reviews` (`:87`) ينشئ سطر مراجعة لكل مرحلة.
- الموافقة تُكمل المرحلة → `_on_tier_approved` (`:124`) → `_activate_next_tier_or_complete` (`:129`) يفعّل المرحلة التالية تلقائياً (ويتعامل مع المراحل غير الحاجبة).

### 1.5 المتطلب المسبق الموجود فعلاً (ربط المستخدم بالنطاق)
`spp_area/models/role.py`: `res.users.role.line.local_area_ids` (Many2many → `spp.area`)، و`res.users.center_area_ids` محسوب، وقاعدة `ir.rule` بـ `area_id child_of` — كلها **حقيقية وجاهزة**.

---

## 2. الفجوة الدقيقة

الأنواع الأربعة لا تحلّ: «المستخدم الحامل **منصب** المرحلة، والذي **نطاقه يغطي منطقة/قبيلة المواطن**».
- `group` يرجع كل الـ500 عاقل (خطأ).
- `field` يقرأ حقلاً واحداً فقط (لا يعبّر عن منصب+نطاق لأربع مراحل).

---

## 3. الامتداد المقترح (رقيق، بالوراثة فقط)

### 3.1 المديول
`alkathiry_approval` يعتمد على `spp_approval` + `spp_area` + `spp_user_roles` + `alkathiry_base` (vocabularies).

### 3.2 الحقول المضافة — على `spp.approval.tier` (وراثة `_inherit`)

| الحقل | النوع | الغرض |
|---|---|---|
| `approval_type` | توسيع عبر `selection_add=[('scoped_position','منصب على نطاق السجل')]` | نوع توثيق جديد |
| `position_id` | Many2one → `spp.vocabulary.code` (domain: namespace المناصب) | منصب المرحلة (عاقل/شيخ/شيخ ضمان…) |
| `scope_kind` | Selection: `area` / `tribe` | هل يطابق نطاق المنطقة أم نطاق القبيلة |
| `scope_source_field` | Char (افتراضي `partner_id.area_id`) | مسار حقل عقدة المواطن على السجل |

> ملاحظة: `position_id` يأتي من vocabulary (`urn:alkathiry:vocab:position`) الذي تضيف اللجنة أكواده من الواجهة → المناصب ديناميكية بالكامل.

### 3.3 المنطق المضاف — تجاوز `get_approvers` (وراثة)

السلوك المطلوب (وصف، لا كود):
```
def get_approvers(self, record):            # _inherit spp.approval.tier
    if self.approval_type == 'scoped_position':
        return self._resolve_scoped_position(record)
    return super().get_approvers(record)    # يحافظ على الأنواع الأربعة كما هي
```
و`_resolve_scoped_position(record)`:
1. استخرج عقدة المواطن من `scope_source_field` (مثلاً `record.partner_id.area_id`).
2. ابحث في `res.users.role.line` عن الأسطر التي:
   - دورها يحمل `position_id` نفسه (المنصب)، **و**
   - `local_area_ids` فيها عقدة تُغطّي عقدة المواطن (`citizen_area parent_path يبدأ بـ role_area parent_path` — أي `child_of`).
3. (لنطاق القبيلة `tribe`: نفس المنطق على `local_tribe_ids` صعوداً في سلسلة عضويات `spp.group.membership`.)
4. أرجِع `res.users` المخوّلين النشطين فقط.

→ النتيجة: المرحلة 1 (عاقل) تُحلّ تلقائياً إلى **عاقل حي المواطن تحديداً** من بين الـ500، والمرحلة 2 (شيخ) إلى **الشيخ الذي يغطي منطقته** (وقد يكون فوق عدة أحياء/عقّال)، وهكذا — مطابق تماماً لسيناريوك.

### 3.4 الواجهات المضافة (Views)
- توسيع نموذج `spp.approval.tier` (form/inline): إظهار `position_id` و`scope_kind` و`scope_source_field` فقط عندما `approval_type == 'scoped_position'` (عبر `invisible="approval_type != 'scoped_position'"`).
- لا واجهات جديدة لتدفّق المراجعة — الجاهزة في `spp_approval` تكفي.

### 3.5 المتطلب المسبق على الأدوار
- المناصب أكواد vocabulary (تضيفها اللجنة).
- ربط الدور بالمنصب: حقل `position_id` على `res.users.role` (أو على `role.line`) — إضافة رقيقة في `alkathiry_roles`.
- النطاق: `local_area_ids` (جاهز) + `local_tribe_ids` (إضافة مقررة).

---

## 4. كيف تضبط اللجنة سلسلة جدة (4 مراحل) من الواجهة — بعد الامتداد

تعريف اعتماد واحد (`spp.approval.definition`, `use_multitier=True`) يخدم **القبائل الخمس** لأنها تشترك في نفس التسلسل؛ التوجيه لكل مواطن يحدث تلقائياً بالنطاق.

| المرحلة (tier) | `approval_type` | `position_id` | `scope_kind` | `min_approvers` |
|---|---|---|---|---|
| 1. عاقل الحي | `scoped_position` | عاقل | area (حي) | 1 |
| 2. الشيخ | `scoped_position` | شيخ | area (منطقة/عدة أحياء) | 1 |
| 3. شيخ الضمان | `scoped_position` | شيخ ضمان | area (محافظة/عدة مشائخ) | 1 |
| 4. اللجنة | `group` (الجاهز) | — | — | 1 أو نِصاب |

> الأرقام (4000 مواطن / 500 عاقل / 300 شيخ / 20 شيخ ضمان) تُدار بلا أي إعداد إضافي: المرحلة لا تخوّل «كل العقّال» بل **عاقل المواطن فقط** عبر مطابقة النطاق.

---

## 5. ما يحدث فعلياً بعد الإضافة (تدفّق حقيقي بأسماء دوال الكود)

1. الموظف يرسل طلب المواطن → `action_submit_for_approval` → ينشئ مراجعة multitier → `_create_tier_reviews` (`approval_review_multitier.py:87`) ينشئ 4 أسطر مراحل، ويفعّل المرحلة 1.
2. `get_approvers(tier1, record)` (المعدّلة) → **عاقل حي المواطن** → يُخطَر عبر mail.activity (`_create_tier_activities`، `approval_tier_review.py:231`).
3. العاقل يوافق (`action_approve`، `:105`) → التحقق من صلاحيته (`:124`) → يُضاف لـ`approved_by_ids` → `_check_tier_completion` (`:150`): `min_approvers=1` متحقق → المرحلة "approved".
4. `_on_tier_approved` → `_activate_next_tier_or_complete` (`:129`) يفعّل المرحلة 2.
5. `get_approvers(tier2, record)` → **الشيخ الذي يغطي منطقة المواطن** (فوق عدة عقّال) → يوافق → المرحلة 3 (شيخ ضمان فوق عدة مشائخ) → المرحلة 4 (اللجنة، `group`).
6. اكتمال كل المراحل الحاجبة → المراجعة "approved" → `spp.approval.mixin` يضبط حالة الطلب إلى موثّق/نشط.

---

## 6. أين/كيف تُضاف (ملخص التنفيذ)

| العنصر | المكان | الطريقة |
|---|---|---|
| نوع التوثيق الجديد + الحقول | `alkathiry_approval/models/approval_tier.py` | `_inherit="spp.approval.tier"` + `selection_add` + حقول |
| منطق الحلّ | نفس الملف | تجاوز `get_approvers` مع `super()` |
| منصب الدور + نطاق قبلي | `alkathiry_roles` | `_inherit="res.users.role(.line)"` + `position_id` + `local_tribe_ids` |
| إظهار الحقول | `alkathiry_approval/views/` | وراثة نموذج tier بـ `invisible` شرطية |
| أكواد المناصب | `alkathiry_base/data` | vocabulary `urn:alkathiry:vocab:position` |

---

## 7. المتوقع بعد الإضافة (المحصلة)
- اللجنة تختار **عدد المراحل** و**منصب** كل مرحلة و**عدد الموثّقين** المطلوب فيها (min_approvers) — من الواجهة، دون كود.
- كل مواطن يُوجَّه تلقائياً، عند كل مرحلة، إلى **صاحب المنصب المسؤول عن نطاقه تحديداً** (عاقل حيّه ثم شيخه ثم شيخ ضمانه ثم اللجنة).
- تبديل أي مسؤول (وفاة/إعفاء) لا يتطلب تعديل الطلبات: لأن `get_approvers` يُقيَّم لحظة كل مرحلة، فالطلبات المعلّقة تنتقل للخلف تلقائياً.
- **لا تفريع (fork) لـ `spp_approval`**: فقط وراثة موديل واحد + تجاوز دالة واحدة + حقول وواجهات. كل تدفّق المراحل والنِصاب والتصعيد وSLA يبقى من الكود الأصلي.

---

**الحالة:** مواصفة جاهزة للاعتماد. عند الموافقة تُنفَّذ ضمن المرحلة P5 (`alkathiry_approval`) المعتمدة في خطة `ARCHITECTURE_REPORT.md`، وبعد توفّر `alkathiry_roles` (المنصب + النطاق).
