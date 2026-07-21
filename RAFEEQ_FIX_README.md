# 🔧 Rafeeq Kernel v2.0.0 - Database Fix Guide

## ⚠️ المشكلة
خطأ في قاعدة البيانات: `column users.ava` (عمود avatar مفقود)

## ✅ الحل

### الخطوة 1: تحديث الكود على Render
```bash
# Pull latest changes from GitHub
git pull origin main
```

### الخطوة 2: إعادة إنشاء جداول قاعدة البيانات
```bash
# Connect to PostgreSQL
psql $DATABASE_URL

# Run the fix SQL
\i rafeeq_db_fix.sql
```

أو يدوياً:
```sql
-- إنشاء جدول المستخدمين مع عمود avatar
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    username        VARCHAR(100) UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    avatar          VARCHAR(500) DEFAULT NULL,  -- ✅ العمود المفقود
    bio             TEXT DEFAULT NULL,
    role            VARCHAR(50) DEFAULT 'user',
    status          VARCHAR(50) DEFAULT 'active',
    email_verified  BOOLEAN DEFAULT FALSE,
    last_login      TIMESTAMP DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول الجلسات
CREATE TABLE IF NOT EXISTS sessions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(500) UNIQUE NOT NULL,
    ip_address      VARCHAR(45) DEFAULT NULL,
    user_agent      TEXT DEFAULT NULL,
    expires_at      TIMESTAMP NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول النشاطات
CREATE TABLE IF NOT EXISTS activities (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action          VARCHAR(100) NOT NULL,
    description     TEXT DEFAULT NULL,
    metadata        JSONB DEFAULT NULL,
    ip_address      VARCHAR(45) DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### الخطوة 3: إعادة تشغيل الخدمة
```bash
# Restart the service on Render
# Go to: https://dashboard.render.com -> dtr1-n -> Manual Deploy -> Clear Build Cache & Deploy
```

## 🔐 بيانات الدخول الافتراضية
- **Email:** `admin@rafeeq.ai`
- **Password:** `admin123`

## 📁 الملفات المُحدَّثة
| الملف | التغيير |
|-------|---------|
| `database.py` | ✅ إضافة عمود avatar + نماذج كاملة |
| `api/auth.py` | ✅ نظام مصادقة كامل (تسجيل/دخول/خروج) |
| `main.py` | ✅ تهيئة DB تلقائية عند البدء |
| `requirements.txt` | ✅ إضافة bcrypt و psycopg2 |
| `Procfile` | ✅ إعداد Render |
| `.env` | ✅ متغيرات البيئة |

## 🧪 اختبار النظام
بعد الإصلاح، افتح:
```
https://dtr1-n.onrender.com/health
```
يجب أن ترى:
```json
{
  "users": 1,
  "sessions": 0,
  "activities": 0,
  "status": "active"
}
```

## 📞 الدعم
إذا استمرت المشكلة، تأكد من:
1. ✅ `DATABASE_URL` صحيح في Render Dashboard
2. ✅ إعادة تشغيل الخدمة بعد التحديث
3. ✅ عدم وجود أخطاء في Build Logs
