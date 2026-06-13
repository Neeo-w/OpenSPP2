# الشرح التفصيلي: المجموعات والعضوية والهرميات وكيف يربطها النظام

> مبني على الكود المصدري الحقيقي في هذا الـ repo (موقع docs.openg2p.org يرجع 403، والكود هو المرجع الأدق والملزِم). كل ادعاء موثّق بـ `ملف:سطر`.

---

## 0. القاعدة الكبرى: كل شيء `res.partner`

في OpenSPP لا يوجد نموذج منفصل للفرد أو المجموعة. **الفرد والمجموعة كلاهما سجل في `res.partner`**، ويُميَّز بينهما بعلمَين (`spp_registry/models/registrant.py:36-37`):

```python
is_registrant = fields.Boolean("Registrant", index=True)   # هل هو ضمن السجل؟
is_group      = fields.Boolean("Group", index=True)        # True=مجموعة/كيان جامع، False=فرد إنسان
```

- **فرد** = `res.partner` بـ `is_registrant=True, is_group=False` → يضيف حقوله النموذج `SPPIndividual` (`individual.py:21 _inherit="res.partner"`): الاسم، تاريخ الميلاد، الجنس… إلخ.
- **مجموعة** = `res.partner` بـ `is_registrant=True, is_group=True` → يضيف حقولها النموذج `SPPGroup` (`group.py:23 _inherit="res.partner"`).

> إذن «الأسرة» و«العشيرة» و«القبيلة» و«الحي» كلها **مجموعات** (`res.partner` بـ `is_group=True`)، و«المواطن» **فرد**.

---

## 1. شرح المصطلحات (واحداً واحداً، من الكود)

### `group` (المجموعة)
سجل `res.partner` بـ `is_group=True`. حقوله المهمة (`group.py`):
- `group_type_id` (`:40`) — **نوع** المجموعة.
- `group_membership_ids` (`:49`) — One2many إلى `spp.group.membership` عبر الحقل `group` = **أعضاء هذه المجموعة**.

### `groups` (المجموعات)
ببساطة جمع `group`؛ مجموعة سجلّات `res.partner` بـ `is_group=True`. لا يوجد نموذج اسمه "groups" — هو نفس `res.partner`.

### `group member` (عضو المجموعة)
ليس حقلاً مباشراً، بل **سجل وسيط** في `spp.group.membership` يربط مجموعةً بعضو. العضو نفسه قد يكون فرداً أو مجموعة (انظر `allow_all_member_type`).

### `group types` (أنواع المجموعات) — `group_type_id`
`group.py:40-44`:
```python
group_type_id = fields.Many2one(
    "spp.vocabulary.code",
    string="Group Type",
    domain="[('namespace_uri', '=', 'urn:openspp:vocab:group-type')]",
)
```
- **نوع المجموعة كود في الـ Vocabulary** ضمن namespace `urn:openspp:vocab:group-type`.
- أي أن أنواع المجموعات (أسرة/عشيرة/قبيلة/حي…) **يضيفها المستخدم من الواجهة** كأكواد vocabulary — لا توجد قائمة ثابتة في الكود.
- مثال: «أسرة»، «عشيرة»، «قبيلة» = ثلاثة أكواد في نفس الـ vocabulary.

### `spp.group.membership` (جسر العضوية) — النموذج المحوري
`spp_registry/models/group_membership.py:11`. **نموذج مستقل** (ليس `res.partner`) يمثّل خط ربط واحد بين مجموعة وعضو:
```python
group      = fields.Many2one("res.partner",
                domain=[("is_group","=",True), ("is_registrant","=",True)])   # الحاوية/الأب  (:16)
individual = fields.Many2one("res.partner",
                domain=[("is_group","=",False),("is_registrant","=",True)])   # العضو/الابن   (:22)
membership_type_ids = fields.Many2many("spp.vocabulary.code",
                domain="namespace = urn:openspp:vocab:group-membership-type")  # دور العضو    (:28)
start_date / ended_date / status / is_ended                                   # صلاحية زمنية  (:60+)
```
- `group` = الأب (الحاوية)، `individual` = العضو.
- **انتبه للقيد الافتراضي:** `individual` نطاقه `is_group=False` → في الـ registry الأساسي **المجموعة تحتوي أفراداً فقط** (نموذج أسرة مسطّح، مستوى واحد فقط).
- `membership_type_ids` = **دور العضو داخل مجموعته** (رب الأسرة/عضو…) — vocabulary مختلف اسمه `group-membership-type`. (تحقّق: قيد «رب أسرة واحد فقط» مطبّق في `group.py:117-120`).

### `group_type_id` مقابل `membership_type_ids` (فرق جوهري)
| الحقل | المكان | المعنى | الـ vocabulary |
|---|---|---|---|
| `group_type_id` | على المجموعة | **ما نوع** هذه المجموعة (أسرة/عشيرة/قبيلة) | `group-type` |
| `membership_type_ids` | على سطر العضوية | **ما دور** العضو داخل مجموعته (رب/عضو) | `group-membership-type` |

### `spp_registry_group_hierarchy` (مفتاح الهرمية متعددة المستويات)
المديول الأساسي يحصر المجموعة في أفراد فقط. هذا المديول **يفتح «مجموعة داخل مجموعة»** بشيئين فقط:

1. يضيف علماً على **نوع المجموعة** (`vocabulary_code.py:16`):
```python
allow_all_member_type = fields.Boolean(
    "Allow group and individual members", default=False,
    help="عند تفعيله على نوع مجموعة، يمكن لمجموعات هذا النوع أن تضم أفراداً ومجموعاتٍ أخرى")
```
2. يجعل نطاق حقل `individual` ديناميكياً (`group_membership.py:18-34`):
```python
domain = [("is_group","=",False), ("is_registrant","=",True)]          # الافتراضي: أفراد فقط
if rec.group.group_type_id.allow_all_member_type:
    domain = [("is_registrant","=",True), ("id","!=",group_id)]         # يسمح بمجموعات أيضاً (ويمنع ربط الذات)
```

### `allow_all_member_type` (المفتاح)
علم على **نوع المجموعة** (كود vocabulary). عند `True`:
- مجموعات هذا النوع تستطيع أن تضم **مجموعات فرعية** (وليس أفراداً فقط).
- هذا هو ما يحوّل «أسرة مسطّحة» إلى **سلسلة هرمية**: قبيلة (allow=True) ⊃ عشيرة (allow=True) ⊃ أسرة (allow=False) ⊃ أفراد.

---

## 2. كيف تُخزَّن الهرمية فعلياً (نقطة المعضلة)

**لا يوجد `parent_id` على `res.partner`.** الهرمية القبلية/العائلية مُعبَّر عنها **بالكامل عبر سلسلة سجلات `spp.group.membership` متتالية**:

```
قبيلة «بني هلال»  (res.partner, is_group=True, group_type=قبيلة[allow_all_member_type=True])
   ▲ membership(group=القبيلة, individual=العشيرة)
عشيرة «س»        (res.partner, is_group=True, group_type=عشيرة[allow=True])
   ▲ membership(group=العشيرة, individual=الأسرة)
أسرة «ص»         (res.partner, is_group=True, group_type=أسرة[allow=False])
   ▲ membership(group=الأسرة, individual=سالم)
سالم            (res.partner, is_group=False)   ← فرد
```

التنقّل في الشجرة (من الكود):
- **الأبناء** (نزولاً): `group.group_membership_ids` (`group.py:49`).
- **الأب** (صعوداً): `node.individual_membership_ids` ثم `.group` (`individual.py:48`: `individual_membership_ids = One2many("spp.group.membership","individual")`؛ يُستخدم فعلاً في `individual.py:122` `line.individual_membership_ids.mapped("group")`).
- النسب الكامل = المشي صعوداً عبر `individual_membership_ids`. (لا closure table — الحساب وقت الاستعلام.)

> **خلاصة المعضلة:** هرمية المسجّلين/العوائل/القبائل **كلها نفس الآلية** = سجلّات `res.partner` (is_group) مربوطة بسلاسل `spp.group.membership`. ما يميّز «عائلة» عن «قبيلة» هو فقط **`group_type_id`** و**`allow_all_member_type`** على ذلك النوع.

---

## 3. هرمية المناطق — آلية مختلفة تماماً (شجرة كلاسيكية)

المناطق **لا** تستخدم العضوية، بل شجرة Odoo التقليدية (`spp_area/models/area_core.py:20`):
```python
_name = "spp.area"
_parent_name = "parent_id"; _parent_store = True       # (:22-23) شجرة حقيقية
parent_id, parent_path (:26,:30)                        # الأب + مسار الشجرة
area_level = compute(parent.area_level + 1)             # (:34,:84) العمق
area_type_id → "spp.area.type"                          # (:36) مستوى/مسمّى الطبقة
code, draft_name                                        # (:29,:31)
```
- `spp.area.type` (`:215+`) — أيضاً شجرة (`_parent_store`)، تعرّف **مسميات المستويات** (دولة/محافظة/مديرية/حي) التي يضيفها المستخدم.
- العمق حر حتى 10 مستويات (`:96`).

---

## 4. الربط بين الهرميات الأربع (جوهر سؤالك)

النظام يربط الهرميات عبر **مرتكزات مشتركة على `res.partner` وعلى المستخدم**:

| الربط | الحقل/الآلية الحقيقية | الموقع |
|---|---|---|
| **المسجّل ⟷ المنطقة** | `res.partner.area_id` → `spp.area` | `spp_area/registrant.py:9` |
| **المسجّل ⟷ الأسرة/القبيلة** | سلاسل `spp.group.membership` | `group_membership.py` |
| **علاقات ثنائية (وليّ أمر/زوج)** | `spp.registry.relationship` (source→destination, relation vocabulary) | `reg_relationship.py:8` |
| **المستخدم ⟷ نطاق المنطقة** | `role.line.local_area_ids` → `user.center_area_ids` (محسوب) → `ir.rule area_id child_of` | `spp_area/role.py:26`، `user.py:9-44`، `rules.xml:26` |

### تفصيل ربط المستخدم بالنطاق (مهم للمناصب)
1. الدور `res.users.role` فيه `role_type = local/global` (`spp_user_roles/role.py:13`).
2. سطر الدور `res.users.role.line` (المسنَد للمستخدم) فيه `local_area_ids` (`spp_area/role.py:26`)، وقيد: الدور المحلي **يجب** أن يملك منطقة (`:38-44`).
3. `user.center_area_ids` يُحسب من كل أسطر الأدوار المحلية (`spp_area/user.py:18-44`).
4. قاعدة `ir.rule`: المستخدم المحلي يرى فقط `area_id child_of center_area_ids` (`rules.xml:26`) — والمستخدم العالمي (اللجنة) يرى الكل.

> هذا هو **الجسر الكامل**: المواطن مربوط بمنطقة (`area_id`) وبقبيلة (membership)، والمستخدم/المسؤول مربوط بنطاق مناطق عبر أدواره. تقاطع «المنطقة المشتركة» هو ما يجعل النظام يعرف «من المسؤول عن هذا المواطن».

---

## 5. مثال عملي كامل للكثيري (كله بنماذج موجودة)

```
# مناطق (spp.area / spp.area.type — شجرة parent_id)
السعودية → منطقة مكة → محافظة جدة → حي السلام        (area_id لكل عقدة)

# قبيلة (res.partner is_group + spp.group.membership — سلاسل عضوية)
قبيلة الكثيري (group_type=قبيلة, allow=True)
   ⊃ عشيرة س (allow=True) ⊃ أسرة ص (allow=False) ⊃ سالم (فرد)

# ربط المواطن
سالم.res.partner: is_registrant=True, is_group=False
   area_id = حي السلام                  ← الربط بالمنطقة
   individual_membership_ids → أسرة ص    ← الربط بالقبيلة/الأسرة

# المسؤول (مستخدم)
أبو محمد.res.users:
   role_line: دور "عاقل" (local), local_area_ids = [حي السلام]
   → center_area_ids = [حي السلام] → يرى مسجّلي حي السلام فقط
```

عند تسجيل سالم في حي السلام، يستطيع النظام إيجاد «عاقل الحي» لأن نطاق دور أبو محمد (`local_area_ids`) يغطي `area_id` الخاص بسالم.

---

## 6. ما هو موجود وجاهز مقابل ما يجب إضافته (بصدق)

| البند | الحالة في الكود |
|---|---|
| فرد/مجموعة على `res.partner` + علمان | ✅ جاهز (`registrant.py:36-37`) |
| نوع المجموعة من vocabulary | ✅ جاهز (`group.py:40`) |
| العضوية + دور العضو + صلاحية زمنية | ✅ جاهز (`group_membership.py`) |
| مجموعة-داخل-مجموعة (هرمية متعددة المستويات) | ✅ جاهز عبر `allow_all_member_type` (`spp_registry_group_hierarchy`) |
| علاقات ثنائية (وليّ أمر/تفويض) | ✅ جاهز (`reg_relationship.py`) |
| شجرة المناطق + مستوياتها | ✅ جاهز (`spp.area` / `spp.area.type`) |
| ربط المسجّل بالمنطقة | ✅ جاهز (`area_id`) |
| ربط المستخدم بنطاق **منطقة** | ✅ جاهز (`local_area_ids` + ir.rule) |
| ربط المستخدم بنطاق **قبيلة** | ❌ يحتاج إضافة `local_tribe_ids` (موازٍ لـ local_area_ids) |
| **المنصب** (عاقل/شيخ) ككيان | ❌ يُضاف ككود vocabulary + حقل على الدور |
| قيد ترتيب مستويات القبيلة (مثلاً منع أن تحتوي أسرةٌ قبيلةً) | ❌ اختياري — يُضاف عبر تحقّق على `group_type` |
| استعلام النسب السريع (closure) | ⚠️ يُحسب وقت الاستعلام؛ نضيف فهرسة عند الحاجة |

---

## 7. الإجابة المباشرة على «كيف يربط النظام الهرميات؟»

النظام **لا** يدمج الهرميات في شجرة واحدة، بل يبقيها **أربع طبقات مستقلة مرتبطة بمرتكزَين على `res.partner`**:
1. **مرتكز المنطقة** = `area_id` (شجرة `spp.area`).
2. **مرتكز القبيلة/الأسرة** = سلاسل `spp.group.membership` (شجرة مجموعات `res.partner`).
3. **طبقة المسجّلين** = `res.partner` نفسها (الأفراد عُقد طرفية، المجموعات عُقد داخلية).
4. **طبقة المناصب/المستخدمين** = `res.users` + أدوار بنطاق (`local_area_ids` حالياً، + `local_tribe_ids` لاحقاً) تتقاطع مع مرتكزَي المنطقة/القبيلة.

والمنصب (عاقل/شيخ) = الجسر بين طبقة المستخدمين والطبقات الثلاث: مستخدمٌ يحمل منصباً على نطاق (منطقة و/أو قبيلة) → يصبح «المسؤول» عن كل فرد يقع داخل ذلك النطاق.

---

**الحالة:** هذا الشرح يثبّت الفهم المشترك للمعضلة. الخطوة التالية المقترحة: اعتماد **مخطط البيانات النهائي للهيكليات** (أنواع المجموعات + أنواع المناطق + المناصب كـ vocabularies + امتداد `local_tribe_ids`) ضمن المرحلتين P1–P2، قبل أي كود.
