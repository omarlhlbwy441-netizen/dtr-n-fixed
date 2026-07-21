"""
╔══════════════════════════════════════════════════════════════════╗
║  Rafeeq Kernel — Container System v2.1                            ║
║  نظام الحاويات المخصص لبيانات تسجيل الدخول فقط                   ║
╚══════════════════════════════════════════════════════════════════╝

Architecture:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  users          │    │  sessions       │    │  login_logs     │
│  (بيانات أساسية) │    │  (جلسات نشطة)   │    │  (سجل الدخول)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
"""

import os
import json
import hashlib
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor

# ═════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═════════════════════════════════════════════════════════════════
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dtr_no_user:GRtFA4nVLhnELSi8xTookZyKasr8XoME@dpg-d9dlnlv7f7vs738ugbe0-a/dtr_no"
)

# ═════════════════════════════════════════════════════════════════
# ENUMS
# ═════════════════════════════════════════════════════════════════
class LoginStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"

class SessionStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOGGED_OUT = "logged_out"

# ═════════════════════════════════════════════════════════════════
# DATA CLASSES — Container Schemas
# ═════════════════════════════════════════════════════════════════

@dataclass
class UserContainer:
    """حاوية المستخدم — البيانات الأساسية فقط"""
    id: int
    email: str
    username: Optional[str]
    password_hash: str
    full_name: Optional[str]
    role: str = "user"
    status: str = "active"
    email_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class SessionContainer:
    """حاوية الجلسة — بيانات تسجيل الدخول النشطة"""
    id: int
    user_id: int
    token: str
    device_info: Optional[str]  # نوع الجهاز
    browser: Optional[str]      # المتصفح
    os_info: Optional[str]      # نظام التشغيل
    ip_address: Optional[str]   # عنوان IP
    location: Optional[str]     # الموقع الجغرافي
    status: str                 # active, expired, revoked, logged_out
    login_time: datetime        # وقت الدخول
    last_activity: datetime     # آخر نشاط
    expires_at: datetime        # وقت الانتهاء
    logout_time: Optional[datetime] = None  # وقت الخروج

@dataclass
class LoginLogContainer:
    """حاوية سجل الدخول — كل محاولات الدخول"""
    id: int
    user_id: Optional[int]      # null if login failed (unknown user)
    email_attempted: str          # البريد المُدخل
    status: str                 # success, failed, suspicious, blocked
    ip_address: Optional[str]
    device_info: Optional[str]
    browser: Optional[str]
    os_info: Optional[str]
    location: Optional[str]
    failure_reason: Optional[str]  # سبب الفشل
    session_token: Optional[str]   # token if successful
    attempt_time: datetime         # وقت المحاولة
    risk_score: int = 0             # درجة الخطورة (0-100)

# ═════════════════════════════════════════════════════════════════
# DATABASE MANAGER — Container Initialization
# ═════════════════════════════════════════════════════════════════

class ContainerManager:
    """مدير الحاويات — إنشاء وصيانة الجداول"""

    @staticmethod
    def get_connection():
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

    @staticmethod
    def init_containers():
        """تهيئة جميع الحاويات"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()

        # ── Container 1: users (البيانات الأساسية) ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
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
            )
        """)

        # ── Container 2: sessions (جلسات تسجيل الدخول) ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token           VARCHAR(500) UNIQUE NOT NULL,
                device_info     VARCHAR(255),
                browser         VARCHAR(255),
                os_info         VARCHAR(255),
                ip_address      VARCHAR(45),
                location        VARCHAR(255),
                status          VARCHAR(50) DEFAULT 'active',
                login_time      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at      TIMESTAMP NOT NULL,
                logout_time     TIMESTAMP,

                CONSTRAINT valid_status CHECK (status IN ('active', 'expired', 'revoked', 'logged_out'))
            )
        """)

        # ── Container 3: login_logs (سجل كل محاولات الدخول) ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
                email_attempted VARCHAR(255) NOT NULL,
                status          VARCHAR(50) NOT NULL,
                ip_address      VARCHAR(45),
                device_info     VARCHAR(255),
                browser         VARCHAR(255),
                os_info         VARCHAR(255),
                location        VARCHAR(255),
                failure_reason  VARCHAR(255),
                session_token   VARCHAR(500),
                attempt_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                risk_score      INTEGER DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),

                CONSTRAINT valid_log_status CHECK (status IN ('success', 'failed', 'suspicious', 'blocked'))
            )
        """)

        # ── Indexes for performance ──
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON login_logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_email ON login_logs(email_attempted)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_time ON login_logs(attempt_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_ip ON login_logs(ip_address)")

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ All containers initialized successfully")
        return True

# ═════════════════════════════════════════════════════════════════
# USER CONTAINER OPERATIONS
# ═════════════════════════════════════════════════════════════════

class UserContainerOps:
    """عمليات حاوية المستخدمين"""

    @staticmethod
    def create(email: str, password: str, username: str = None, 
                 full_name: str = None, role: str = "user") -> Optional[Dict]:
        """إنشاء مستخدم جديد"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        try:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cursor.execute("""
                INSERT INTO users (email, username, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, username, full_name, role, status, created_at
            """, (email, username, hashed, full_name, role))
            user = cursor.fetchone()
            conn.commit()
            return dict(user)
        except psycopg2.IntegrityError:
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        """البحث بالبريد"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(user) if user else None

    @staticmethod
    def verify_password(email: str, password: str) -> Optional[Dict]:
        """التحقق من كلمة المرور"""
        user = UserContainerOps.get_by_email(email)
        if not user:
            return None
        if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return user
        return None

    @staticmethod
    def update_status(user_id: int, status: str):
        """تحديث حالة المستخدم"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = %s, updated_at = %s WHERE id = %s",
                      (status, datetime.now(), user_id))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def count() -> int:
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM users")
        result = cursor.fetchone()["c"]
        cursor.close()
        conn.close()
        return result

# ═════════════════════════════════════════════════════════════════
# SESSION CONTAINER OPERATIONS
# ═════════════════════════════════════════════════════════════════

class SessionContainerOps:
    """عمليات حاوية الجلسات — بيانات تسجيل الدخول فقط"""

    @staticmethod
    def _parse_user_agent(user_agent: str) -> Dict[str, str]:
        """تحليل معلومات الجهاز من User-Agent"""
        device = "Unknown"
        browser = "Unknown"
        os_info = "Unknown"

        if user_agent:
            ua = user_agent.lower()
            # Browser detection
            if "chrome" in ua: browser = "Chrome"
            elif "firefox" in ua: browser = "Firefox"
            elif "safari" in ua: browser = "Safari"
            elif "edge" in ua: browser = "Edge"
            elif "opera" in ua: browser = "Opera"

            # OS detection
            if "windows" in ua: os_info = "Windows"
            elif "mac" in ua: os_info = "macOS"
            elif "linux" in ua: os_info = "Linux"
            elif "android" in ua: os_info = "Android"
            elif "iphone" in ua or "ipad" in ua: os_info = "iOS"

            # Device type
            if "mobile" in ua: device = "Mobile"
            elif "tablet" in ua: device = "Tablet"
            else: device = "Desktop"

        return {"device": device, "browser": browser, "os": os_info}

    @staticmethod
    def create(user_id: int, ip_address: str = None, user_agent: str = None,
               location: str = None, expires_hours: int = 24) -> Dict:
        """إنشاء جلسة جديدة"""
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(hours=expires_hours)
        device_data = SessionContainerOps._parse_user_agent(user_agent)

        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (user_id, token, device_info, browser, os_info, 
                                ip_address, location, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (user_id, token, device_data["device"], device_data["browser"],
              device_data["os"], ip_address, location, expires))
        session = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return dict(session)

    @staticmethod
    def get_by_token(token: str) -> Optional[Dict]:
        """الحصول على جلسة حسب التوكن"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, u.email, u.username, u.full_name, u.role
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = %s AND s.status = 'active' AND s.expires_at > %s
        """, (token, datetime.now()))
        session = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(session) if session else None

    @staticmethod
    def update_activity(token: str):
        """تحديث آخر نشاط"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions SET last_activity = %s WHERE token = %s
        """, (datetime.now(), token))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def logout(token: str, reason: str = "user_logout"):
        """تسجيل خروج — حفظ وقت الخروج"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET status = 'logged_out', logout_time = %s 
            WHERE token = %s
        """, (datetime.now(), token))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def revoke_all_user_sessions(user_id: int, reason: str = "security"):
        """إلغاء جميع جلسات المستخدم"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET status = 'revoked', logout_time = %s 
            WHERE user_id = %s AND status = 'active'
        """, (datetime.now(), user_id))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_user_sessions(user_id: int) -> List[Dict]:
        """جميع جلسات المستخدم"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions WHERE user_id = %s ORDER BY login_time DESC
        """, (user_id,))
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(s) for s in sessions]

    @staticmethod
    def count_active() -> int:
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as c FROM sessions 
            WHERE status = 'active' AND expires_at > %s
        """, (datetime.now(),))
        result = cursor.fetchone()["c"]
        cursor.close()
        conn.close()
        return result

    @staticmethod
    def cleanup_expired():
        """تنظيف الجلسات المنتهية"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET status = 'expired' 
            WHERE status = 'active' AND expires_at < %s
        """, (datetime.now(),))
        conn.commit()
        cursor.close()
        conn.close()

# ═════════════════════════════════════════════════════════════════
# LOGIN LOG CONTAINER OPERATIONS
# ═════════════════════════════════════════════════════════════════

class LoginLogContainerOps:
    """عمليات حاوية سجل الدخول — كل محاولات الدخول"""

    @staticmethod
    def _calculate_risk_score(email: str, ip: str, status: str, 
                               recent_attempts: int) -> int:
        """حساب درجة الخطورة"""
        score = 0
        if status == "failed":
            score += 20
        if recent_attempts > 3:
            score += 30
        if recent_attempts > 5:
            score += 40
        return min(score, 100)

    @staticmethod
    def log_attempt(email: str, status: str, user_id: int = None,
                    ip_address: str = None, user_agent: str = None,
                    location: str = None, failure_reason: str = None,
                    session_token: str = None):
        """تسجيل محاولة دخول"""
        device_data = SessionContainerOps._parse_user_agent(user_agent)

        # Count recent attempts from this IP
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as c FROM login_logs 
            WHERE ip_address = %s AND attempt_time > %s
        """, (ip_address, datetime.now() - timedelta(hours=1)))
        recent = cursor.fetchone()["c"]

        risk = LoginLogContainerOps._calculate_risk_score(
            email, ip_address, status, recent
        )

        cursor.execute("""
            INSERT INTO login_logs (user_id, email_attempted, status, ip_address,
                                   device_info, browser, os_info, location,
                                   failure_reason, session_token, risk_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, email, status, ip_address, device_data["device"],
              device_data["browser"], device_data["os"], location,
              failure_reason, session_token, risk))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_user_history(user_id: int, limit: int = 50) -> List[Dict]:
        """سجل دخول المستخدم"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM login_logs 
            WHERE user_id = %s 
            ORDER BY attempt_time DESC 
            LIMIT %s
        """, (user_id, limit))
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(l) for l in logs]

    @staticmethod
    def get_recent_suspicious(limit: int = 20) -> List[Dict]:
        """محاولات مشبوهة"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM login_logs 
            WHERE status IN ('failed', 'suspicious', 'blocked') 
               OR risk_score > 50
            ORDER BY attempt_time DESC 
            LIMIT %s
        """, (limit,))
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(l) for l in logs]

    @staticmethod
    def get_stats() -> Dict:
        """إحصائيات الدخول"""
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as c FROM login_logs WHERE status = 'success'")
        success = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM login_logs WHERE status = 'failed'")
        failed = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM login_logs WHERE status = 'suspicious'")
        suspicious = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM login_logs WHERE attempt_time > %s",
                      (datetime.now() - timedelta(hours=24),))
        last_24h = cursor.fetchone()["c"]

        cursor.close()
        conn.close()

        return {
            "total_success": success,
            "total_failed": failed,
            "total_suspicious": suspicious,
            "last_24h_attempts": last_24h,
            "success_rate": round(success / (success + failed) * 100, 2) if (success + failed) > 0 else 0
        }

    @staticmethod
    def count() -> int:
        conn = ContainerManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM login_logs")
        result = cursor.fetchone()["c"]
        cursor.close()
        conn.close()
        return result

# ═════════════════════════════════════════════════════════════════
# AUTHENTICATION SERVICE — Uses Container System
# ═════════════════════════════════════════════════════════════════

class AuthService:
    """خدمة المصادقة — تستخدم نظام الحاويات"""

    @staticmethod
    def register(email: str, password: str, username: str = None,
                 full_name: str = None, ip: str = None, user_agent: str = None) -> Dict:
        """تسجيل مستخدم جديد"""
        # Create user
        user = UserContainerOps.create(email, password, username, full_name)
        if not user:
            # Log failed registration attempt
            LoginLogContainerOps.log_attempt(
                email=email, status="failed", ip_address=ip,
                user_agent=user_agent, failure_reason="Email already exists"
            )
            return {"success": False, "error": "Email already registered"}

        # Log success
        LoginLogContainerOps.log_attempt(
            email=email, status="success", user_id=user["id"],
            ip_address=ip, user_agent=user_agent
        )

        # Create session
        session = SessionContainerOps.create(
            user_id=user["id"], ip_address=ip, user_agent=user_agent
        )

        return {
            "success": True,
            "user": user,
            "token": session["token"]
        }

    @staticmethod
    def login(email: str, password: str, ip: str = None, 
              user_agent: str = None, location: str = None) -> Dict:
        """تسجيل الدخول"""
        # Verify user
        user = UserContainerOps.verify_password(email, password)

        if not user:
            LoginLogContainerOps.log_attempt(
                email=email, status="failed", ip_address=ip,
                user_agent=user_agent, location=location,
                failure_reason="Invalid credentials"
            )
            return {"success": False, "error": "Invalid email or password"}

        # Check user status
        if user["status"] != "active":
            LoginLogContainerOps.log_attempt(
                email=email, status="blocked", user_id=user["id"],
                ip_address=ip, user_agent=user_agent, location=location,
                failure_reason=f"Account is {user['status']}"
            )
            return {"success": False, "error": f"Account is {user['status']}"}

        # Create session
        session = SessionContainerOps.create(
            user_id=user["id"], ip_address=ip, user_agent=user_agent,
            location=location
        )

        # Log successful login
        LoginLogContainerOps.log_attempt(
            email=email, status="success", user_id=user["id"],
            ip_address=ip, user_agent=user_agent, location=location,
            session_token=session["token"]
        )

        return {
            "success": True,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"]
            },
            "token": session["token"],
            "session": {
                "device": session["device_info"],
                "browser": session["browser"],
                "os": session["os_info"],
                "expires": session["expires_at"].isoformat() if session["expires_at"] else None
            }
        }

    @staticmethod
    def logout(token: str, ip: str = None):
        """تسجيل الخروج"""
        session = SessionContainerOps.get_by_token(token)
        if session:
            SessionContainerOps.logout(token)
            LoginLogContainerOps.log_attempt(
                email=session["email"], status="success", user_id=session["user_id"],
                ip_address=ip, session_token=token, failure_reason="User logout"
            )
        return {"success": True}

    @staticmethod
    def validate_session(token: str) -> Optional[Dict]:
        """التحقق من صلاحية الجلسة"""
        session = SessionContainerOps.get_by_token(token)
        if session:
            SessionContainerOps.update_activity(token)
        return session

    @staticmethod
    def get_login_history(user_id: int) -> List[Dict]:
        """سجل دخول المستخدم الكامل"""
        return LoginLogContainerOps.get_user_history(user_id)

    @staticmethod
    def get_active_sessions(user_id: int) -> List[Dict]:
        """الجلسات النشطة للمستخدم"""
        return SessionContainerOps.get_user_sessions(user_id)

    @staticmethod
    def revoke_all_sessions(user_id: int):
        """إلغاء جميع الجلسات"""
        SessionContainerOps.revoke_all_user_sessions(user_id)
        return {"success": True}

# ═════════════════════════════════════════════════════════════════
# SYSTEM STATS
# ═════════════════════════════════════════════════════════════════

def get_container_stats() -> Dict:
    """إحصائيات نظام الحاويات"""
    return {
        "containers": {
            "users": {
                "total": UserContainerOps.count(),
                "description": "بيانات المستخدمين الأساسية"
            },
            "sessions": {
                "active": SessionContainerOps.count_active(),
                "description": "جلسات تسجيل الدخول النشطة"
            },
            "login_logs": {
                "total": LoginLogContainerOps.count(),
                "stats": LoginLogContainerOps.get_stats(),
                "description": "سجل كل محاولات الدخول"
            }
        },
        "system": {
            "status": "active",
            "version": "2.1.0",
            "timestamp": datetime.now().isoformat()
        }
    }

# ═════════════════════════════════════════════════════════════════
# FASTAPI ROUTES
# ═════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[dict] = None

def get_client_info(request: Request):
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "location": request.headers.get("x-forwarded-for", "")
    }

@auth_router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, request: Request):
    client = get_client_info(request)
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")

    result = AuthService.register(
        email=data.email, password=data.password,
        username=data.username, full_name=data.full_name,
        ip=client["ip"], user_agent=client["user_agent"]
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return AuthResponse(
        success=True, message="Registration successful",
        token=result["token"], user=result["user"]
    )

@auth_router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, request: Request):
    client = get_client_info(request)
    result = AuthService.login(
        email=data.email, password=data.password,
        ip=client["ip"], user_agent=client["user_agent"],
        location=client["location"]
    )

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])

    return AuthResponse(
        success=True, message="Login successful",
        token=result["token"], user=result["user"]
    )

@auth_router.post("/logout")
async def logout(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    client = get_client_info(request)
    AuthService.logout(token, ip=client["ip"])
    return {"success": True, "message": "Logged out"}

@auth_router.get("/me")
async def get_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    session = AuthService.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    return {
        "success": True,
        "user": {
            "id": session["user_id"],
            "email": session["email"],
            "username": session["username"],
            "full_name": session["full_name"],
            "role": session["role"]
        }
    }

@auth_router.get("/sessions")
async def get_sessions(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    session = AuthService.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    sessions = AuthService.get_active_sessions(session["user_id"])
    return {"success": True, "sessions": sessions}

@auth_router.get("/history")
async def get_history(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    session = AuthService.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    history = AuthService.get_login_history(session["user_id"])
    return {"success": True, "history": history}

@auth_router.get("/stats")
async def auth_stats():
    return get_container_stats()

# Export
__all__ = [
    "ContainerManager", "UserContainerOps", "SessionContainerOps",
    "LoginLogContainerOps", "AuthService", "get_container_stats",
    "auth_router"
]
