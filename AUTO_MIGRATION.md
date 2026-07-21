# 🔧 Rafeeq Kernel — Auto-Migration System v2.2

## نظام تحديث تلقائي للجداول مع حفظ البيانات

```
┌─────────────────────────────────────────────────────────────────┐
│                    Rafeeq Kernel v2.2.0                        │
│              Auto-Migration Edition 🔧                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ Define   │ -> │ Detect   │ -> │ Generate │ -> │ Execute  │ │
│  │ Schema   │    │ Changes  │    │ Migration│    │ Safely   │ │
│  │ (Python) │    │ (Diff)   │    │ (SQL)    │    │ (Backup) │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │ Track    │    │ History  │    │ Rollback │                  │
│  │ Version  │    │ Log      │    │ Support  │                  │
│  └──────────┘    └──────────┘    └──────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 كيف يعمل؟

### 1. تعريف المخطط (Schema Definition)
```python
# في ملف auto_migration.py — أضف جدول جديد هنا

new_table = TableDef(
    name="user_profiles",
    description="ملفات المستخدمين التعريفية",
    columns=[
        ColumnDef(name="id", type=SQLType.SERIAL, primary_key=True, nullable=False),
        ColumnDef(name="user_id", type=SQLType.INTEGER, references="users.id", on_delete="CASCADE"),
        ColumnDef(name="avatar", type=SQLType.STRING, length=500),
        ColumnDef(name="bio", type=SQLType.TEXT),
        ColumnDef(name="phone", type=SQLType.STRING, length=50),
        ColumnDef(name="country", type=SQLType.STRING, length=100),
        ColumnDef(name="created_at", type=SQLType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
    ],
    indexes=[
        {"columns": ["user_id"], "unique": True},
    ]
)

# أضفه في قائمة tables:
return SchemaDef(
    version="2.3.0",  # رفع الإصدار
    tables=[users_table, sessions_table, login_logs_table, new_table]
)
```

### 2. اكتشاف تلقائي (Auto-Detect)
النظام يقارن المخطط الجديد مع الجداول الموجودة في قاعدة البيانات:
- ✅ جدول جديد → `CREATE TABLE`
- ✅ عمود جديد → `ADD COLUMN`
- ✅ تغيير نوع → `ALTER COLUMN TYPE`
- ✅ تغيير nullable → `ALTER COLUMN SET/DROP NOT NULL`
- ⚠️ عمود محذوف → تحذير (لا يحذف تلقائياً)

### 3. نسخ احتياطي (Auto-Backup)
قبل أي تغيير:
```sql
CREATE TABLE users_backup_20260721_143052 AS SELECT * FROM users;
```

### 4. تنفيذ (Execute)
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR(500);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles ("user_id");
```

### 5. تتبع (Track)
```sql
INSERT INTO __migrations__ (version, schema_hash, sql_commands, ...)
VALUES ('2.3.0', 'abc123...', 'ALTER TABLE...', ...);
```

---

## 📡 API Endpoints

### التحديث التلقائي
| Endpoint | Method | وصف |
|----------|--------|-----|
| `/migrate/run` | POST | تشغيل التحديث التلقائي |
| `/migrate/status` | GET | حالة التحديثات |
| `/migrate/preview` | GET | معاينة التغييرات قبل التنفيذ |
| `/migrate/history` | GET | سجل التحديثات |
| `/migrate/rollback/{id}` | POST | التراجع عن تحديث |
| `/migrate/schema` | GET | تعريف المخطط الحالي |

### أمثلة

**معاينة التغييرات:**
```bash
curl https://dtr1-n.onrender.com/migrate/preview
```

**تشغيل التحديث:**
```bash
curl -X POST https://dtr1-n.onrender.com/migrate/run
```

**حالة التحديثات:**
```bash
curl https://dtr1-n.onrender.com/migrate/status
```

---

## 📊 هيكل جداول التتبع

### `__migrations__` — سجل التحديثات
```sql
CREATE TABLE __migrations__ (
    id              SERIAL PRIMARY KEY,
    version         VARCHAR(50) NOT NULL,      -- إصدار المخطط
    schema_hash     VARCHAR(32) NOT NULL,      -- hash فريد
    description     TEXT,                       -- وصف
    sql_commands    TEXT NOT NULL,             -- الأوامر المنفذة
    tables_affected TEXT[],                    -- الجداول المتأثرة
    backup_info     JSONB,                     -- معلومات النسخ الاحتياطي
    executed_at     TIMESTAMP,                 -- وقت التنفيذ
    duration_ms     INTEGER,                   -- المدة
    status          VARCHAR(20),               -- success/failed
    error_message   TEXT                       -- رسالة الخطأ
);
```

### `__schema_version__` — إصدار المخطط الحالي
```sql
CREATE TABLE __schema_version__ (
    id          SERIAL PRIMARY KEY,
    version     VARCHAR(50) NOT NULL,
    schema_hash VARCHAR(32) NOT NULL,
    tables      TEXT[],
    applied_at  TIMESTAMP,
    is_current  BOOLEAN DEFAULT TRUE
);
```

---

## 🔄 إضافة جدول جديد — خطوة بخطوة

### الخطوة 1: افتح `auto_migration.py`

### الخطوة 2: أضف تعريف الجدول في `get_current_schema()`
```python
# ── Table 4: user_profiles ──
user_profiles_table = TableDef(
    name="user_profiles",
    description="ملفات المستخدمين التعريفية",
    columns=[
        ColumnDef(name="id", type=SQLType.SERIAL, primary_key=True, nullable=False),
        ColumnDef(name="user_id", type=SQLType.INTEGER, nullable=False, 
                 references="users.id", on_delete="CASCADE"),
        ColumnDef(name="avatar", type=SQLType.STRING, length=500),
        ColumnDef(name="bio", type=SQLType.TEXT),
        ColumnDef(name="phone", type=SQLType.STRING, length=50),
        ColumnDef(name="country", type=SQLType.STRING, length=100),
        ColumnDef(name="created_at", type=SQLType.TIMESTAMP, 
                 default="CURRENT_TIMESTAMP"),
    ],
    indexes=[
        {"columns": ["user_id"], "unique": True, "name": "idx_profiles_user"},
    ]
)
```

### الخطوة 3: أضف الجدول في القائمة
```python
return SchemaDef(
    version="2.3.0",  # رفع الإصدار!
    tables=[
        users_table,
        sessions_table, 
        login_logs_table,
        user_profiles_table,  # <-- الجديد
    ]
)
```

### الخطوة 4: ارفع على GitHub
```bash
git add auto_migration.py
git commit -m "Add user_profiles table"
git push origin main
```

### الخطوة 5: أعد التشغيل على Render
```
Dashboard → Manual Deploy → Clear Build Cache & Deploy
```

### النتيجة 🎉
النظام سيعمل تلقائياً:
1. يكتشف الجدول الجديد
2. ينشئ نسخة احتياطية
3. ينشئ الجدول
4. ينشئ الفهارس
5. يسجل التحديث

---

## 🛡️ قواعد الأمان

| القاعدة | الوصف |
|---------|-------|
| **لا حذف تلقائي** | الأعمدة المفقودة تحذير فقط |
| **نسخ احتياطي** | نسخة قبل كل تغيير |
| **Rollback** | إمكانية التراجع |
| **Preview** | معاينة قبل التنفيذ |
| **Version tracking** | تتبع كل إصدار |

---

## 📁 الملفات

| الملف | الوصف |
|-------|-------|
| `auto_migration.py` | نظام التحديث التلقائي |
| `database.py` | نظام الحاويات |
| `main.py` | نقطة البدء + تشغيل تلقائي |

---

**Rafeeq Kernel v2.2.0 — Auto-Migration Edition** 🔧
*من بعد فضل الله اشكر دولة مصر لانها اتاحت لي فرصة لكي اقوم بهذا العمل*
