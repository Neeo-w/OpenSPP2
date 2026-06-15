# فحص الواجهات الحالية للمجموعات + إصلاح هيكلة القبائل

> مبني على الكود الفعلي. يصف ما يراه/يعبّئه المستخدم اليوم عند إضافة قبيلة، وكيف يرتبط، ثم الإصلاح المنظّم المضاف.

---

## 1. أين توجد المجموعات في النظام (الواجهات الحالية)

- **القائمة:** Registry → **Groups** (`action_groups_list`، `spp_registry/views/group_views.xml:131`)
  - دومين: `[('is_registrant','=',True),('is_group','=',True)]` (السطر 139) → كل المجموعات (أسر/قبائل/أي نوع).
  - عرض القائمة (`view_groups_list_tree`): **الاسم، العنوان، الهاتف، الوسوم**.
- **النموذج:** يستخدم **نفس نموذج الفرد** `view_individuals_form` (السطر 161) مع قسم `group_detail` يظهر فقط عند `is_group=True`.

---

## 2. ما الذي يعبّئه المستخدم عند إضافة قبيلة (حقول نموذج المجموعة)

من قسم `group_detail` في `individual_views.xml` + إضافات المديولات:

| الحقل | المصدر | الربط |
|---|---|---|
| **Group Name** (`name`) | spp_registry | اسم القبيلة/العشيرة |
| **Group Type** (`group_type_id`) | spp_registry | Many2one → `spp.vocabulary.code` (vocab `group-type`). هنا تظهر مستويات النسب التي بذرناها (قبيلة كبرى/قبيلة/عشيرة/حي) |
| **Area** (`area_id`) | spp_area (`group_views.xml:14`) | Many2one → `spp.area` (شجرة الجغرافيا) |
| **Tags** (`tags_ids`) | spp_registry | vocab `registrant-tags` |
| **Email / Phone Numbers** | spp_registry | `spp.phone.number` (مع `country_id`) |
| **Identity Documents** (`reg_ids`) | spp_registry | `spp.registry.id` (هوية المجموعة إن لزم) |
| **Group Members** (`group_membership_ids`) | spp_registry + hierarchy | القسم المحوري ↓ |

### قسم الأعضاء (Group Members) — جوهر الهرمية
في `group_membership_views.xml` (الأساسي) أعمدة العضو: **Member Name، تاريخ الميلاد، الجنس، Group Role (`membership_type_ids`)، تاريخ البدء/الانتهاء، الحالة**.

- النموذج الأساسي يثبّت `domain="[('is_group','=',False)]"` → **أفراد فقط**.
- **لكن** `spp_registry_group_hierarchy/views/group_views.xml:13-17` **يتجاوز** هذا الدومين إلى `individual_domain` الديناميكي، فيصبح: إذا كان نوع المجموعة `allow_all_member_type=True` → **يُسمح بإضافة مجموعات فرعية كأعضاء** (group-of-groups). كما يضيف نموذج «Child» لإضافة عضو-مجموعة (السطر 41-78).

> ✅ **النتيجة:** ما دام `spp_registry_group_hierarchy` مثبّتاً (وهو تبعية لـ `alkathiry_base`)، فإن بناء شجرة قبيلة ⊃ عشيرة ⊃ أسرة ⊃ أفراد **يعمل فعلاً** من واجهة الأعضاء.

---

## 3. كيف ترتبط واجهة المجموعة بالواجهات/العمليات الأخرى

```
المجموعة (res.partner, is_group)
 ├─ group_type_id  → vocab group-type        (واجهة Vocabularies: يضيف المستخدم مستويات)
 ├─ area_id        → spp.area                (واجهة Areas: شجرة الجغرافيا)
 ├─ group_membership_ids → spp.group.membership
 │     ├─ individual  → فرد أو مجموعة فرعية   (يفتح نموذج الفرد عبر زر)
 │     └─ membership_type_ids → vocab group-membership-type (دور: رب/عضو)
 ├─ reg_ids        → spp.registry.id          (الهوية)
 └─ المشاركة       → spp_programs (برامج/دورات/استحقاقات عبر العضوية)
```

---

## 4. ما الذي «يحتاج هيكلة» فعلاً (التشخيص الصادق)

| البند | الحالة | الحكم |
|---|---|---|
| إضافة مجموعات فرعية (شجرة) | يعمل عبر hierarchy | ✅ سليم |
| مستويات النسب قابلة للاختيار | بذرناها في group-type | ✅ سليم |
| **واجهة مخصّصة لبناء شجرة القبيلة** | غير موجودة — تُبنى ضمن «Groups» العامة المختلطة بالأسر/الأنواع الأخرى | ❌ يحتاج إصلاح |
| **منع احتواء غير صحيح** (عشيرة تحتوي قبيلة) | لا قيد | ⚠️ تحسين لاحق |

**الإصلاح المنفّذ الآن:** واجهة/قائمة **«Tribal Structure»** مخصّصة، مفلترة على مستويات النسب فقط (`group_type_id.code in [grand_tribe, tribe, clan, neighborhood]`)، تعرض الاسم + النوع + المنطقة، وتفتح نفس نموذج المجموعة الصحيح — فيصبح بناء شجرة القبيلة عملية **منظّمة ومنفصلة** عن المجموعات العامة.

**مؤجّل (قرار):** قيد ترتيب المستويات (منع الاحتواء العكسي) — يُضاف كـ `@api.constrains` عند الطلب.

---

**الحالة:** التقرير + الإصلاح المنظّم (قائمة Tribal Structure) منفّذان. قيد ترتيب المستويات بانتظار قرارك.
