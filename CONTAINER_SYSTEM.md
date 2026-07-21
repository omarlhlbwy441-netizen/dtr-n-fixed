# 🏗️ Rafeeq Kernel — Container System v2.1

## نظام الحاويات المخصص لبيانات تسجيل الدخول

```
┌─────────────────────────────────────────────────────────────────┐
│                    Rafeeq Kernel v2.1.0                         │
│                  Container Edition 🏗️                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │   users      │   │  sessions    │   │ login_logs   │       │
│  │  (حاوية 1)   │   │  (حاوية 2)  │   │  (حاوية 3)   │       │
│  ├──────────────┤   ├──────────────┤   ├──────────────┤       │
│  │ • id         │   │ • id         │   │ • id         │       │
│  │ • email      │   │ • user_id    │   │ • user_id    │       │
│  │ • username   │   │ • token      │   │ • email      │       │
│  │ • password   │   │ • device     │   │ • status     │       │
│  │ • full_name  │   │ • browser    │   │ • ip         │       │
│  │ • role       │   │ • os         │   │ • device     │       │
│  │ • status     │   │ • ip         │   │ • browser    │       │
│  │ • created_at │   │ • location   │   │ • os         │       │
│  └──────────────┘   │ • login_time │   │ • location   │       │
│                     │ • expires    │   │ • reason     │       │
│                     │ • logout_time│   │ • risk_score │       │
│                     └──────────────┘   │ • attempt_time│      │
│                                        └──────────────┘       │
│                                                                 │
│  💡 كل حاوية منفصلة ومحمية — بيانات تسجيل الدخول فقط!         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 الحاويات الثلاث

### 1️⃣ حاوية `users` — البيانات الأساسية
```sql
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    username        VARCHAR(100) UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(50) DEFAULT 'user',
    status          VARCHAR(50) DEFAULT 'active',
    email_verified  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**الغرض:** حفظ بيانات المستخدم الأساسية فقط (بدون avatar أو bio)

---

### 2️⃣ حاوية `sessions` — الجلسات النشطة
```sql
CREATE TABLE sessions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(500) UNIQUE NOT NULL,
    device_info     VARCHAR(255),      -- Mobile/Desktop/Tablet
    browser         VARCHAR(255),      -- Chrome/Firefox/Safari
    os_info         VARCHAR(255),      -- Windows/macOS/Android
    ip_address      VARCHAR(45),
    location        VARCHAR(255),
    status          VARCHAR(50),       -- active/expired/revoked/logged_out
    login_time      TIMESTAMP,
    last_activity   TIMESTAMP,
    expires_at      TIMESTAMP NOT NULL,
    logout_time     TIMESTAMP          -- وقت الخروج الفعلي
);
```
**الغرض:** تتبع كل جلسة تسجيل دخول مع بيانات الجهاز الكاملة

---

### 3️⃣ حاوية `login_logs` — سجل الدخول الكامل
```sql
CREATE TABLE login_logs (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    email_attempted VARCHAR(255) NOT NULL,
    status          VARCHAR(50),       -- success/failed/suspicious/blocked
    ip_address      VARCHAR(45),
    device_info     VARCHAR(255),
    browser         VARCHAR(255),
    os_info         VARCHAR(255),
    location        VARCHAR(255),
    failure_reason  VARCHAR(255),      -- سبب الفشل
    session_token   VARCHAR(500),      -- token if successful
    attempt_time    TIMESTAMP,
    risk_score      INTEGER DEFAULT 0  -- درجة الخطورة 0-100
);
```
**الغرض:** سجل **كل** محاولات الدخول (ناجحة وفاشلة) للأمان

---

## 🔐 مميزات النظام

| الميزة | الوصف |
|--------|-------|
| 🏗️ **3 حاويات منفصلة** | كل نوع بيانات في حاوية خاصة |
| 📱 **Device Fingerprinting** | تحديد نوع الجهاز والمتصفح ونظام التشغيل |
| ⚠️ **Risk Scoring** | درجة خطورة 0-100 لكل محاولة دخول |
| 📜 **Full Audit Trail** | سجل كامل لكل محاولات الدخول |
| 🚪 **Logout Tracking** | تسجيل وقت الخروج الفعلي |
| 🧹 **Auto Cleanup** | تنظيف الجلسات المنتهية تلقائياً |
| 🔒 **Session Revocation** | إلغاء جميع جلسات المستخدم فوراً |

---

## 🚀 API Endpoints

### المصادقة
| Endpoint | Method | وصف |
|----------|--------|-----|
| `/auth/register` | POST | تسجيل مستخدم جديد |
| `/auth/login` | POST | تسجيل الدخول |
| `/auth/logout` | POST | تسجيل الخروج |
| `/auth/me` | GET | معلومات المستخدم الحالي |

### إدارة الجلسات
| Endpoint | Method | وصف |
|----------|--------|-----|
| `/auth/sessions` | GET | جميع جلسات المستخدم |
| `/auth/history` | GET | سجل دخول المستخدم الكامل |
| `/auth/stats` | GET | إحصائيات النظام |

---

## 📊 مثال على الاستجابة

### تسجيل الدخول الناجح
```json
{
  "success": true,
  "message": "Login successful",
  "token": "abc123...",
  "user": {
    "id": 1,
    "email": "user@rafeeq.ai",
    "username": "user123",
    "role": "user"
  },
  "session": {
    "device": "Mobile",
    "browser": "Chrome",
    "os": "Android",
    "expires": "2026-07-22T12:00:00"
  }
}
```

### إحصائيات النظام
```json
{
  "containers": {
    "users": { "total": 5, "description": "بيانات المستخدمين الأساسية" },
    "sessions": { "active": 3, "description": "جلسات تسجيل الدخول النشطة" },
    "login_logs": {
      "total": 25,
      "stats": {
        "total_success": 20,
        "total_failed": 5,
        "success_rate": 80.0
      }
    }
  }
}
```

---

## 🔧 التفعيل على Render

1. **سحب التحديثات:**
   ```bash
   git pull origin main
   ```

2. **إعادة تشغيل الخدمة:**
   - Render Dashboard → Manual Deploy → Clear Build Cache & Deploy

3. **التحقق:**
   ```
   https://dtr1-n.onrender.com/health
   ```

---

**Rafeeq Kernel v2.1.0 — Container Edition** 🏗️
*من بعد فضل الله اشكر دولة مصر لانها اتاحت لي فرصة لكي اقوم بهذا العمل*
