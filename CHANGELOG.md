# CHANGELOG — DTR-N / Rafeeq Kernel

## v2.3.0 — 2026-07-27

### 🐛 إصلاحات (Bug Fixes)
- **render.yaml**: تصحيح أمر التشغيل من `gunicorn app:app` إلى `uvicorn api.main:app`
- **requirements.txt**: إضافة `httpx`, `gunicorn`, `aiofiles`, `python-jose`, `passlib` الناقصة
- **evolution_engine.py**: إضافة دالة `create_engine()` المفقودة التي يستدعيها `api/main.py`
- **main.py**: إضافة import الناقص لـ `datetime`

### ✨ مميزات جديدة (New Features)

#### نظام الوكلاء الفرعيين في الخلفية (`dtr_n/sub_agents.py`)
- `SecuritySubAgent` — مراقبة الأمان كل دقيقتين
- `TesterSubAgent` — اختبار تلقائي لنقاط API كل 5 دقائق
- `OptimizerSubAgent` — قياس الأداء كل 10 دقائق
- `MobileUpdateSubAgent` — إدارة تحديثات الجوال كل 30 دقيقة
- `SubAgentCoordinator` — منسق يُطلق جميع الوكلاء عند بدء التطبيق

#### وكلاء رئيسيون جدد (`dtr_n/agents.py`)
- 🛡️ **Security Agent** — يكتشف التهديدات ويراجع الأمان
- 🚀 **Deployer Agent** — ينشر التحديثات على Render/GitHub
- 🧪 **Tester Agent** — يختبر الكود تلقائياً
- ⚡ **Optimizer Agent** — يحسّن الأداء
- 📱 **Mobile Agent** — يدير تحديثات تطبيق الجوال
- 🧠 **Sub-Coordinator** — يُشرف على الوكلاء الفرعيين

#### تحديث تطبيق الجوال — Mobile App Update Function
نقاط API جديدة في `main.py` و `api/main.py`:

| Endpoint | Method | وصف |
|----------|--------|-----|
| `/api/mobile/update-check` | GET/POST | فحص وجود تحديث للتطبيق |
| `/api/mobile/register-device` | POST | تسجيل جهاز وجلب معلومات التحديث |
| `/api/mobile/version` | GET | الإصدار الحالي وإعدادات القناة |
| `/api/sub-agents` | GET | حالة الوكلاء الفرعيين |
| `/api/sub-agents/start` | POST | تشغيل الوكلاء الفرعيين |
| `/api/sub-agents/stop` | POST | إيقاف الوكلاء الفرعيين |

#### مثال استخدام تحديث الجوال
```bash
# تحقق إذا كانت نسخة 2.1.0 تحتاج تحديث
curl "https://your-app.onrender.com/api/mobile/update-check?version=2.1.0&platform=android"

# الرد
{
  "has_update": true,
  "force_update": false,
  "current_version": "2.1.0",
  "latest_version": "2.3.0",
  "min_supported_version": "2.0.0",
  "channel": "stable",
  "release_notes": {"ar": "تحسينات في الأداء...", "en": "..."},
  "download_url": "https://github.com/.../releases/tag/v2.3.0"
}
```

### 🔗 ربط الأنظمة (System Integration)
- `api/main.py` يُشغّل `SubAgentCoordinator` تلقائياً عند startup
- `artifacts/api-server/src/routes/dtrn-proxy.ts` يُوجّه جميع نقاط الجوال والوكلاء الفرعيين
- جميع نقاط API متاحة عبر `/api/dtrn/*` (proxy) وعبر Python مباشرة

---

## v2.2.1 — سابقاً
- إصلاح الاستيرادات المتداخلة (Circular Imports)
- دمج `database.py` و `auto_migration.py` في ملف واحد
