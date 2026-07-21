"""
================================================================================
DTR-N SESSION & RESOURCE MANAGER
نظام إدارة الجلسات والموارد

1 جلسة DTR-N = 2 جلسات Kimi = 50 خطوة
================================================================================
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger("dtr-n.resources")


class PlanTier(Enum):
    """باقات الاشتراك"""
    FREE = "free"           # مجاني
    SILVER = "silver"       # فضي
    GOLD = "gold"           # ذهبي
    DIAMOND = "diamond"     # ماسي


class SessionResourceManager:
    """
    مدير الجلسات والموارد في DTR-N

    كل جلسة = 50 خطوة (ضعف Kimi)
    """

    # إعدادات الباقات
    PLAN_CONFIG = {
        PlanTier.FREE: {
            "daily_sessions": 3,           # 3 جلسات يومياً
            "steps_per_session": 50,        # 50 خطوة لكل جلسة
            "daily_diamonds": 50,           # 50 ماس يومياً
            "code_generations": 5,          # 5 توليدات كود
            "github_pushes": 2,             # 2 رفع GitHub
            "evolution_cycles": 1,          # 1 دورة تطور
            "storage_mb": 100,              # 100 MB تخزين
            "priority": "low",                # أولوية منخفضة
        },
        PlanTier.SILVER: {
            "daily_sessions": 5,
            "steps_per_session": 50,
            "daily_diamonds": 150,
            "code_generations": 15,
            "github_pushes": 10,
            "evolution_cycles": 3,
            "storage_mb": 500,
            "priority": "normal",
        },
        PlanTier.GOLD: {
            "daily_sessions": 10,
            "steps_per_session": 50,
            "daily_diamonds": 400,
            "code_generations": 40,
            "github_pushes": 30,
            "evolution_cycles": 10,
            "storage_mb": 2000,
            "priority": "high",
        },
        PlanTier.DIAMOND: {
            "daily_sessions": 50,           # غير محدود عملياً
            "steps_per_session": 50,
            "daily_diamonds": 2000,
            "code_generations": 200,
            "github_pushes": 100,
            "evolution_cycles": 50,
            "storage_mb": 10000,
            "priority": "highest",
        },
    }

    def __init__(self, db_manager=None):
        self.db = db_manager
        self._init_storage()

    def _init_storage(self):
        """تهيئة التخزين"""
        if self.db and hasattr(self.db, '_is_postgres') and self.db._is_postgres():
            self._init_postgres_tables()
        else:
            self._init_mock_storage()

    def _init_postgres_tables(self):
        """إنشاء جداول الموارد في PostgreSQL"""
        try:
            with self.db.conn.cursor() as cur:
                # جدول استخدام الموارد
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_resources (
                        user_id VARCHAR(50) PRIMARY KEY,
                        plan_tier VARCHAR(50) DEFAULT 'free',
                        daily_sessions_used INT DEFAULT 0,
                        daily_steps_used INT DEFAULT 0,
                        daily_diamonds_used INT DEFAULT 0,
                        code_generations_used INT DEFAULT 0,
                        github_pushes_used INT DEFAULT 0,
                        evolution_cycles_used INT DEFAULT 0,
                        storage_used_mb INT DEFAULT 0,
                        last_reset_date DATE DEFAULT CURRENT_DATE,
                        total_sessions_all_time INT DEFAULT 0,
                        total_steps_all_time INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # جدول سجل الجلسات
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS session_logs (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(50) NOT NULL,
                        session_number INT NOT NULL,
                        steps_used INT DEFAULT 0,
                        steps_remaining INT DEFAULT 50,
                        features_used JSONB DEFAULT '{}',
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'active',
                        project_name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # جدول خطوات الجلسة الواحدة
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS session_steps (
                        id SERIAL PRIMARY KEY,
                        session_id INT REFERENCES session_logs(id),
                        step_number INT NOT NULL,
                        action_type VARCHAR(100),
                        description TEXT,
                        tokens_used INT DEFAULT 0,
                        execution_time_ms INT DEFAULT 0,
                        success BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                self.db.conn.commit()
                logger.info("[Resources] PostgreSQL tables initialized")
        except Exception as e:
            logger.error(f"[Resources] Failed to init PostgreSQL: {e}")

    def _init_mock_storage(self):
        """تهيئة تخزين محلي"""
        self.mock_resources = {}
        self.mock_sessions = []
        logger.info("[Resources] Mock storage initialized")

    # =========================================================================
    # USER RESOURCE MANAGEMENT
    # =========================================================================

    async def get_or_create_user_resources(self, user_id: str, plan: PlanTier = PlanTier.FREE) -> Dict:
        """الحصول على موارد المستخدم أو إنشاؤها"""
        if self.db and hasattr(self.db, '_is_postgres') and self.db._is_postgres():
            try:
                with self.db.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_resources (user_id, plan_tier)
                        VALUES (%s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING *
                    """, (user_id, plan.value))
                    row = cur.fetchone()
                    return {
                        "user_id": row[0],
                        "plan_tier": row[1],
                        "daily_sessions_used": row[2],
                        "daily_steps_used": row[3],
                        "daily_diamonds_used": row[4],
                        "code_generations_used": row[5],
                        "github_pushes_used": row[6],
                        "evolution_cycles_used": row[7],
                        "storage_used_mb": row[8],
                        "last_reset_date": str(row[9]),
                        "total_sessions_all_time": row[10],
                        "total_steps_all_time": row[11],
                    }
            except Exception as e:
                logger.error(f"[Resources] get_or_create error: {e}")

        # Mock fallback
        if user_id not in self.mock_resources:
            self.mock_resources[user_id] = {
                "user_id": user_id,
                "plan_tier": plan.value,
                "daily_sessions_used": 0,
                "daily_steps_used": 0,
                "daily_diamonds_used": 0,
                "code_generations_used": 0,
                "github_pushes_used": 0,
                "evolution_cycles_used": 0,
                "storage_used_mb": 0,
                "last_reset_date": datetime.now().date().isoformat(),
                "total_sessions_all_time": 0,
                "total_steps_all_time": 0,
            }
        return self.mock_resources[user_id]

    async def check_and_reset_daily(self, user_id: str) -> Dict:
        """التحقق من إعادة تعيين الموارد اليومية"""
        resources = await self.get_or_create_user_resources(user_id)
        today = datetime.now().date().isoformat()

        if resources["last_reset_date"] != today:
            # إعادة تعيين الموارد اليومية
            plan = PlanTier(resources["plan_tier"])
            config = self.PLAN_CONFIG[plan]

            if self.db and hasattr(self.db, '_is_postgres') and self.db._is_postgres():
                try:
                    with self.db.conn.cursor() as cur:
                        cur.execute("""
                            UPDATE user_resources SET
                                daily_sessions_used = 0,
                                daily_steps_used = 0,
                                daily_diamonds_used = 0,
                                code_generations_used = 0,
                                github_pushes_used = 0,
                                evolution_cycles_used = 0,
                                last_reset_date = CURRENT_DATE,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = %s
                        """, (user_id,))
                except Exception as e:
                    logger.error(f"[Resources] Reset error: {e}")
            else:
                resources["daily_sessions_used"] = 0
                resources["daily_steps_used"] = 0
                resources["daily_diamonds_used"] = 0
                resources["code_generations_used"] = 0
                resources["github_pushes_used"] = 0
                resources["evolution_cycles_used"] = 0
                resources["last_reset_date"] = today

            logger.info(f"[Resources] Daily reset for user {user_id}")

        return await self.get_or_create_user_resources(user_id)

    async def get_remaining_resources(self, user_id: str) -> Dict:
        """الحصول على الموارد المتبقية"""
        resources = await self.check_and_reset_daily(user_id)
        plan = PlanTier(resources["plan_tier"])
        config = self.PLAN_CONFIG[plan]

        return {
            "user_id": user_id,
            "plan": plan.value,
            "sessions": {
                "used": resources["daily_sessions_used"],
                "total": config["daily_sessions"],
                "remaining": config["daily_sessions"] - resources["daily_sessions_used"],
            },
            "steps": {
                "used": resources["daily_steps_used"],
                "total": config["daily_sessions"] * config["steps_per_session"],
                "remaining": (config["daily_sessions"] * config["steps_per_session"]) - resources["daily_steps_used"],
            },
            "diamonds": {
                "used": resources["daily_diamonds_used"],
                "total": config["daily_diamonds"],
                "remaining": config["daily_diamonds"] - resources["daily_diamonds_used"],
            },
            "code_generations": {
                "used": resources["code_generations_used"],
                "total": config["code_generations"],
                "remaining": config["code_generations"] - resources["code_generations_used"],
            },
            "github_pushes": {
                "used": resources["github_pushes_used"],
                "total": config["github_pushes"],
                "remaining": config["github_pushes"] - resources["github_pushes_used"],
            },
            "evolution_cycles": {
                "used": resources["evolution_cycles_used"],
                "total": config["evolution_cycles"],
                "remaining": config["evolution_cycles"] - resources["evolution_cycles_used"],
            },
            "storage": {
                "used_mb": resources["storage_used_mb"],
                "total_mb": config["storage_mb"],
                "remaining_mb": config["storage_mb"] - resources["storage_used_mb"],
            },
            "all_time": {
                "total_sessions": resources["total_sessions_all_time"],
                "total_steps": resources["total_steps_all_time"],
            },
            "comparison": {
                "dtrn_session_steps": config["steps_per_session"],
                "kimi_session_steps": 25,
                "advantage": "2x",
                "description": "1 جلسة DTR-N = 2 جلسات Kimi (50 vs 25 خطوة)"
            }
        }

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    async def start_new_session(self, user_id: str, project_name: str = "") -> Dict:
        """بدء جلسة جديدة"""
        resources = await self.check_and_reset_daily(user_id)
        plan = PlanTier(resources["plan_tier"])
        config = self.PLAN_CONFIG[plan]

        # التحقق من توفر جلسات
        if resources["daily_sessions_used"] >= config["daily_sessions"]:
            return {
                "success": False,
                "error": "Daily session limit reached",
                "limit": config["daily_sessions"],
                "used": resources["daily_sessions_used"],
                "upgrade_required": True,
            }

        # إنشاء الجلسة
        session_number = resources["total_sessions_all_time"] + 1

        if self.db and hasattr(self.db, '_is_postgres') and self.db._is_postgres():
            try:
                with self.db.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO session_logs (user_id, session_number, steps_remaining, project_name)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (user_id, session_number, config["steps_per_session"], project_name))
                    session_id = cur.fetchone()[0]

                    # تحديث استخدام المستخدم
                    cur.execute("""
                        UPDATE user_resources SET
                            daily_sessions_used = daily_sessions_used + 1,
                            total_sessions_all_time = total_sessions_all_time + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (user_id,))
            except Exception as e:
                logger.error(f"[Resources] Start session error: {e}")
                session_id = session_number
        else:
            session_id = session_number
            self.mock_sessions.append({
                "id": session_id,
                "user_id": user_id,
                "session_number": session_number,
                "steps_used": 0,
                "steps_remaining": config["steps_per_session"],
                "status": "active",
                "project_name": project_name,
            })
            resources["daily_sessions_used"] += 1
            resources["total_sessions_all_time"] += 1

        return {
            "success": True,
            "session_id": session_id,
            "session_number": session_number,
            "steps_total": config["steps_per_session"],
            "steps_remaining": config["steps_per_session"],
            "plan": plan.value,
            "message": f"Session {session_number} started | {config['steps_per_session']} steps available (2x Kimi)",
        }

    async def use_step(self, session_id: int, action_type: str, description: str, tokens: int = 0) -> Dict:
        """استخدام خطوة في الجلسة"""
        if self.db and hasattr(self.db, '_is_postgres') and self.db._is_postgres():
            try:
                with self.db.conn.cursor() as cur:
                    # تسجيل الخطوة
                    cur.execute("""
                        INSERT INTO session_steps (session_id, step_number, action_type, description, tokens_used)
                        VALUES (%s, (SELECT COALESCE(MAX(step_number), 0) + 1 FROM session_steps WHERE session_id = %s), %s, %s, %s)
                        RETURNING step_number
                    """, (session_id, session_id, action_type, description, tokens))
                    step_number = cur.fetchone()[0]

                    # تحديث الجلسة
                    cur.execute("""
                        UPDATE session_logs SET
                            steps_used = steps_used + 1,
                            steps_remaining = steps_remaining - 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING steps_used, steps_remaining
                    """, (session_id,))
                    row = cur.fetchone()

                    return {
                        "success": True,
                        "step_number": step_number,
                        "steps_used": row[0],
                        "steps_remaining": row[1],
                        "action": action_type,
                    }
            except Exception as e:
                logger.error(f"[Resources] Use step error: {e}")

        # Mock fallback
        for session in self.mock_sessions:
            if session["id"] == session_id:
                session["steps_used"] += 1
                session["steps_remaining"] -= 1
                return {
                    "success": True,
                    "step_number": session["steps_used"],
                    "steps_used": session["steps_used"],
                    "steps_remaining": session["steps_remaining"],
                    "action": action_type,
                }

        return {"success": False, "error": "Session not found"}

    async def end_session(self, session_id: int) -> Dict:
        """إنهاء الجلسة"""
        if self.db and hasattr(self.db, '_is_postgres') and self.db._is_postgres():
            try:
                with self.db.conn.cursor() as cur:
                    cur.execute("""
                        UPDATE session_logs SET
                            status = 'completed',
                            end_time = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING user_id, steps_used, steps_remaining
                    """, (session_id,))
                    row = cur.fetchone()

                    # تحديث إجمالي الخطوات
                    cur.execute("""
                        UPDATE user_resources SET
                            daily_steps_used = daily_steps_used + %s,
                            total_steps_all_time = total_steps_all_time + %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (row[1], row[1], row[0]))

                    return {
                        "success": True,
                        "session_id": session_id,
                        "steps_used": row[1],
                        "steps_remaining": row[2],
                    }
            except Exception as e:
                logger.error(f"[Resources] End session error: {e}")

        # Mock fallback
        for session in self.mock_sessions:
            if session["id"] == session_id:
                session["status"] = "completed"
                return {
                    "success": True,
                    "session_id": session_id,
                    "steps_used": session["steps_used"],
                    "steps_remaining": session["steps_remaining"],
                }

        return {"success": False, "error": "Session not found"}

    # =========================================================================
    # CONSUMPTION CHECKS
    # =========================================================================

    async def can_use_feature(self, user_id: str, feature: str) -> Dict:
        """التحقق من إمكانية استخدام ميزة"""
        resources = await self.get_remaining_resources(user_id)

        feature_map = {
            "code_generation": "code_generations",
            "github_push": "github_pushes",
            "evolution_cycle": "evolution_cycles",
            "diamond": "diamonds",
        }

        resource_key = feature_map.get(feature, feature)
        if resource_key in resources:
            remaining = resources[resource_key]["remaining"]
            return {
                "allowed": remaining > 0,
                "feature": feature,
                "remaining": remaining,
                "message": f"{remaining} {feature} remaining" if remaining > 0 else f"No {feature} remaining. Upgrade your plan!",
            }

        return {"allowed": True, "feature": feature, "message": "No limit for this feature"}

    async def consume_resource(self, user_id: str, resource_type: str, amount: int = 1) -> Dict:
        """استهلاك مورد"""
        if self.db and hasattr(self.db, '_is_postgres') and self.db._is_postgres():
            try:
                column_map = {
                    "code_generation": "code_generations_used",
                    "github_push": "github_pushes_used",
                    "evolution_cycle": "evolution_cycles_used",
                    "diamond": "daily_diamonds_used",
                }
                column = column_map.get(resource_type, resource_type + "_used")

                with self.db.conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE user_resources SET
                            {column} = {column} + %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                        RETURNING {column}
                    """, (amount, user_id))
                    row = cur.fetchone()

                    return {
                        "success": True,
                        "resource": resource_type,
                        "consumed": amount,
                        "total_used": row[0],
                    }
            except Exception as e:
                logger.error(f"[Resources] Consume error: {e}")

        # Mock fallback
        resources = await self.get_or_create_user_resources(user_id)
        if resource_type == "code_generation":
            resources["code_generations_used"] += amount
        elif resource_type == "github_push":
            resources["github_pushes_used"] += amount
        elif resource_type == "evolution_cycle":
            resources["evolution_cycles_used"] += amount
        elif resource_type == "diamond":
            resources["daily_diamonds_used"] += amount

        return {
            "success": True,
            "resource": resource_type,
            "consumed": amount,
        }

    # =========================================================================
    # ANALYTICS & REPORTING
    # =========================================================================

    async def get_session_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """الحصول على سجل الجلسات"""
        if self.db and hasattr(self.db, '_is_postgres') and self.db._is_postgres():
            try:
                with self.db.conn.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM session_logs
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (user_id, limit))
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
            except Exception as e:
                logger.error(f"[Resources] History error: {e}")

        # Mock fallback
        return [s for s in self.mock_sessions if s.get("user_id") == user_id][:limit]

    async def get_usage_stats(self, user_id: str) -> Dict:
        """إحصائيات الاستخدام"""
        resources = await self.get_remaining_resources(user_id)
        history = await self.get_session_history(user_id)

        total_steps_used = sum(s.get("steps_used", 0) for s in history)
        avg_steps_per_session = total_steps_used / len(history) if history else 0

        return {
            "user_id": user_id,
            "plan": resources["plan"],
            "sessions_today": resources["sessions"]["used"],
            "sessions_total": resources["all_time"]["total_sessions"],
            "steps_today": resources["steps"]["used"],
            "steps_total": resources["all_time"]["total_steps"],
            "avg_steps_per_session": round(avg_steps_per_session, 1),
            "efficiency": f"{round((avg_steps_per_session / 50) * 100, 1)}%" if history else "0%",
            "comparison": {
                "dtrn_total_steps_available": resources["steps"]["total"],
                "kimi_equivalent": resources["steps"]["total"] // 25,
                "advantage": "2x more steps per session",
            },
            "recent_sessions": len(history),
        }


# =========================================================================
# SINGLETON INSTANCE
# =========================================================================

_resource_manager = None

def get_resource_manager(db_manager=None):
    """الحصول على مدير الموارد (Singleton)"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = SessionResourceManager(db_manager)
    return _resource_manager
