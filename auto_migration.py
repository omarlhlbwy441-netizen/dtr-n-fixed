"""
╔══════════════════════════════════════════════════════════════════╗
║  Rafeeq Kernel — Auto-Migration System v2.2                       ║
║  نظام تحديث تلقائي للجداول مع حفظ البيانات                       ║
╚══════════════════════════════════════════════════════════════════╝

Flow:
Define Schema -> Detect Changes -> Generate Migration -> Execute Safely
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
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

MIGRATIONS_TABLE = "__migrations__"
SCHEMA_VERSION_TABLE = "__schema_version__"

# ═════════════════════════════════════════════════════════════════
# SQL TYPES
# ═════════════════════════════════════════════════════════════════

class SQLType(Enum):
    STRING = "VARCHAR"
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SERIAL = "SERIAL"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    DATE = "DATE"
    TIME = "TIME"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE PRECISION"
    DECIMAL = "DECIMAL"
    JSON = "JSON"
    JSONB = "JSONB"
    UUID = "UUID"
    BYTEA = "BYTEA"
    INET = "INET"
    CIDR = "CIDR"

# ═════════════════════════════════════════════════════════════════
# SCHEMA DEFINITION
# ═════════════════════════════════════════════════════════════════

@dataclass
class ColumnDef:
    name: str
    type: SQLType
    length: Optional[int] = None
    nullable: bool = True
    default: Any = None
    primary_key: bool = False
    unique: bool = False
    index: bool = False
    references: Optional[str] = None
    on_delete: Optional[str] = None
    check_constraint: Optional[str] = None

    def to_sql(self) -> str:
        parts = [f'"{self.name}"']
        if self.length and self.type == SQLType.STRING:
            parts.append(f"{self.type.value}({self.length})")
        else:
            parts.append(self.type.value)
        if self.primary_key:
            parts.append("PRIMARY KEY")
        if not self.nullable:
            parts.append("NOT NULL")
        if self.unique and not self.primary_key:
            parts.append("UNIQUE")
        if self.default is not None:
            if isinstance(self.default, str):
                parts.append(f"DEFAULT '{self.default}'")
            elif isinstance(self.default, bool):
                parts.append(f"DEFAULT {'TRUE' if self.default else 'FALSE'}")
            else:
                parts.append(f"DEFAULT {self.default}")
        if self.references:
            ref = self.references.split(".")
            if len(ref) == 2:
                parts.append(f"REFERENCES {ref[0]}({ref[1]})")
                if self.on_delete:
                    parts.append(f"ON DELETE {self.on_delete}")
        if self.check_constraint:
            parts.append(f"CHECK ({self.check_constraint})")
        return " ".join(parts)

@dataclass
class TableDef:
    name: str
    columns: List[ColumnDef]
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    description: Optional[str] = None

    def get_column(self, name: str) -> Optional[ColumnDef]:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def to_create_sql(self) -> str:
        col_defs = ",\n    ".join([col.to_sql() for col in self.columns])
        sql = f"CREATE TABLE IF NOT EXISTS {self.name} (\n    {col_defs}\n)"
        if self.constraints:
            sql += "\n" + "\n".join(self.constraints)
        return sql

    def to_index_sql(self) -> List[str]:
        sqls = []
        for idx in self.indexes:
            idx_name = idx.get("name", f"idx_{self.name}_{'_'.join(idx['columns'])}")
            cols = ", ".join([f'"{c}"' for c in idx["columns"]])
            unique = "UNIQUE " if idx.get("unique") else ""
            sqls.append(f"CREATE {unique}INDEX IF NOT EXISTS {idx_name} ON {self.name} ({cols})")
        return sqls

@dataclass
class SchemaDef:
    version: str
    tables: List[TableDef]
    created_at: datetime = field(default_factory=datetime.now)

    def get_table(self, name: str) -> Optional[TableDef]:
        for tbl in self.tables:
            if tbl.name == name:
                return tbl
        return None

    def to_hash(self) -> str:
        schema_str = json.dumps({
            "version": self.version,
            "tables": [
                {
                    "name": t.name,
                    "columns": [{"name": c.name, "type": c.type.value, "nullable": c.nullable}
                               for c in t.columns]
                }
                for t in self.tables
            ]
        }, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]

# ═════════════════════════════════════════════════════════════════
# MIGRATION ENGINE
# ═════════════════════════════════════════════════════════════════

class MigrationEngine:
    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url
        self._init_migration_tables()

    def _get_connection(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _init_migration_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                id SERIAL PRIMARY KEY,
                version VARCHAR(50) NOT NULL,
                schema_hash VARCHAR(32) NOT NULL,
                description TEXT,
                sql_commands TEXT NOT NULL,
                tables_affected TEXT[],
                backup_info JSONB,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_ms INTEGER,
                status VARCHAR(20) DEFAULT 'success',
                error_message TEXT
            )
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
                id SERIAL PRIMARY KEY,
                version VARCHAR(50) NOT NULL,
                schema_hash VARCHAR(32) NOT NULL,
                tables TEXT[],
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT TRUE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    def get_current_schema_version(self) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * FROM {SCHEMA_VERSION_TABLE}
            WHERE is_current = TRUE
            ORDER BY applied_at DESC LIMIT 1
        """)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(result) if result else None

    def get_table_schema(self, table_name: str) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = %s ORDER BY ordinal_position
        """, (table_name,))
        columns = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(c) for c in columns]

    def detect_changes(self, new_schema: SchemaDef) -> List[Dict]:
        changes = []
        for table in new_schema.tables:
            existing = self.get_table_schema(table.name)
            if not existing:
                changes.append({
                    "type": "CREATE_TABLE",
                    "table": table.name,
                    "sql": table.to_create_sql(),
                    "indexes": table.to_index_sql()
                })
            else:
                existing_cols = {c["column_name"]: c for c in existing}
                for col in table.columns:
                    if col.name not in existing_cols:
                        changes.append({
                            "type": "ADD_COLUMN",
                            "table": table.name,
                            "column": col.name,
                            "sql": f'ALTER TABLE {table.name} ADD COLUMN IF NOT EXISTS {col.to_sql()}',
                            "column_def": col
                        })
                    else:
                        existing_col = existing_cols[col.name]
                        existing_type = existing_col["data_type"]
                        new_type = col.type.value.lower()
                        if existing_type != new_type and not (
                            existing_type == "character varying" and new_type == "varchar" or
                            existing_type == "timestamp without time zone" and new_type == "timestamp"
                        ):
                            changes.append({
                                "type": "ALTER_COLUMN",
                                "table": table.name,
                                "column": col.name,
                                "old_type": existing_type,
                                "new_type": new_type,
                                "sql": f'ALTER TABLE {table.name} ALTER COLUMN "{col.name}" TYPE {col.type.value}',
                                "warning": "Type change may cause data loss!"
                            })
                        existing_nullable = existing_col["is_nullable"] == "YES"
                        if existing_nullable != col.nullable:
                            null_sql = "SET NOT NULL" if not col.nullable else "DROP NOT NULL"
                            changes.append({
                                "type": "ALTER_NULLABLE",
                                "table": table.name,
                                "column": col.name,
                                "sql": f'ALTER TABLE {table.name} ALTER COLUMN "{col.name}" {null_sql}'
                            })
                for existing_col_name in existing_cols:
                    if not table.get_column(existing_col_name):
                        changes.append({
                            "type": "REMOVE_COLUMN_WARNING",
                            "table": table.name,
                            "column": existing_col_name,
                            "warning": f"Column '{existing_col_name}' exists in DB but not in schema. Manual removal required.",
                            "sql": f"-- WARNING: Manual removal required"
                        })
        return changes

    def generate_migration_sql(self, changes: List[Dict]) -> Tuple[str, List[str]]:
        sql_commands = []
        tables_affected = []
        for change in changes:
            if change["type"] == "CREATE_TABLE":
                sql_commands.append(change["sql"])
                sql_commands.extend(change.get("indexes", []))
                tables_affected.append(change["table"])
            elif change["type"] in ["ADD_COLUMN", "ALTER_COLUMN", "ALTER_NULLABLE"]:
                sql_commands.append(change["sql"])
                if change["table"] not in tables_affected:
                    tables_affected.append(change["table"])
            elif change["type"] == "REMOVE_COLUMN_WARNING":
                sql_commands.append(f"-- {change['warning']}")
        return ";\n".join(sql_commands), tables_affected

    def backup_table(self, table_name: str) -> str:
        backup_name = f"{table_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}")
            conn.commit()
            cursor.close()
            conn.close()
            return backup_name
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return f"FAILED: {str(e)}"

    def execute_migration(self, new_schema: SchemaDef, description: str = "") -> Dict:
        start_time = datetime.now()
        changes = self.detect_changes(new_schema)
        if not changes:
            return {"success": True, "message": "No changes detected. Schema is up to date.", "changes": [], "duration_ms": 0}

        migration_sql, tables_affected = self.generate_migration_sql(changes)
        backups = {}
        for table in tables_affected:
            if any(c["type"] != "CREATE_TABLE" for c in changes if c.get("table") == table):
                backups[table] = self.backup_table(table)

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            for sql in migration_sql.split(";\n"):
                sql = sql.strip()
                if sql and not sql.startswith("--"):
                    cursor.execute(sql)
            conn.commit()

            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            schema_hash = new_schema.to_hash()

            cursor.execute(f"""
                INSERT INTO {MIGRATIONS_TABLE}
                (version, schema_hash, description, sql_commands, tables_affected, backup_info, duration_ms, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (new_schema.version, schema_hash, description or f"Auto-migration to {new_schema.version}",
                  migration_sql, tables_affected, json.dumps(backups), duration, "success"))

            cursor.execute(f"UPDATE {SCHEMA_VERSION_TABLE} SET is_current = FALSE")
            cursor.execute(f"""
                INSERT INTO {SCHEMA_VERSION_TABLE} (version, schema_hash, tables, is_current)
                VALUES (%s, %s, %s, TRUE)
            """, (new_schema.version, schema_hash, tables_affected))
            conn.commit()

            result = {
                "success": True,
                "message": "Migration completed successfully",
                "version": new_schema.version,
                "schema_hash": schema_hash,
                "changes_count": len(changes),
                "changes": changes,
                "tables_affected": tables_affected,
                "backups": backups,
                "duration_ms": duration,
                "sql_executed": migration_sql
            }
        except Exception as e:
            conn.rollback()
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            cursor.execute(f"""
                INSERT INTO {MIGRATIONS_TABLE}
                (version, schema_hash, description, sql_commands, tables_affected, duration_ms, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (new_schema.version, new_schema.to_hash(), f"FAILED: Auto-migration to {new_schema.version}",
                  migration_sql, tables_affected, duration, "failed", str(e)))
            conn.commit()
            result = {"success": False, "error": str(e), "version": new_schema.version, "changes": changes, "sql_attempted": migration_sql}
        finally:
            cursor.close()
            conn.close()
        return result

    def get_migration_history(self, limit: int = 50) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {MIGRATIONS_TABLE} ORDER BY executed_at DESC LIMIT %s", (limit,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(r) for r in results]

    def rollback_migration(self, migration_id: int) -> Dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {MIGRATIONS_TABLE} WHERE id = %s", (migration_id,))
        migration = cursor.fetchone()
        if not migration:
            return {"success": False, "error": "Migration not found"}
        backups = json.loads(migration["backup_info"] or "{}")
        restored = []
        for table, backup in backups.items():
            if not backup.startswith("FAILED"):
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                cursor.execute(f"ALTER TABLE {backup} RENAME TO {table}")
                restored.append(table)
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Rollback completed for migration {migration_id}", "restored_tables": restored}

# ═════════════════════════════════════════════════════════════════
# SCHEMA REGISTRY
# ═════════════════════════════════════════════════════════════════

class SchemaRegistry:
    @staticmethod
    def get_current_schema() -> SchemaDef:
        users_table = TableDef(
            name="users",
            description="Users basic data",
            columns=[
                ColumnDef(name="id", type=SQLType.SERIAL, primary_key=True, nullable=False),
                ColumnDef(name="email", type=SQLType.STRING, length=255, nullable=False, unique=True),
                ColumnDef(name="username", type=SQLType.STRING, length=100, unique=True),
                ColumnDef(name="password_hash", type=SQLType.STRING, length=255, nullable=False),
                ColumnDef(name="full_name", type=SQLType.STRING, length=255),
                ColumnDef(name="role", type=SQLType.STRING, length=50, default="user"),
                ColumnDef(name="status", type=SQLType.STRING, length=50, default="active"),
                ColumnDef(name="email_verified", type=SQLType.BOOLEAN, default=False),
                ColumnDef(name="created_at", type=SQLType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
                ColumnDef(name="updated_at", type=SQLType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            ],
            indexes=[
                {"columns": ["email"], "name": "idx_users_email"},
                {"columns": ["username"], "name": "idx_users_username"},
                {"columns": ["status"], "name": "idx_users_status"},
                {"columns": ["role"], "name": "idx_users_role"},
            ]
        )

        sessions_table = TableDef(
            name="sessions",
            description="Active login sessions",
            columns=[
                ColumnDef(name="id", type=SQLType.SERIAL, primary_key=True, nullable=False),
                ColumnDef(name="user_id", type=SQLType.INTEGER, nullable=False, references="users.id", on_delete="CASCADE"),
                ColumnDef(name="token", type=SQLType.STRING, length=500, nullable=False, unique=True),
                ColumnDef(name="device_info", type=SQLType.STRING, length=255),
                ColumnDef(name="browser", type=SQLType.STRING, length=255),
                ColumnDef(name="os_info", type=SQLType.STRING, length=255),
                ColumnDef(name="ip_address", type=SQLType.INET),
                ColumnDef(name="location", type=SQLType.STRING, length=255),
                ColumnDef(name="status", type=SQLType.STRING, length=50, default="active",
                         check_constraint="status IN ('active', 'expired', 'revoked', 'logged_out')"),
                ColumnDef(name="login_time", type=SQLType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
                ColumnDef(name="last_activity", type=SQLType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
                ColumnDef(name="expires_at", type=SQLType.TIMESTAMP, nullable=False),
                ColumnDef(name="logout_time", type=SQLType.TIMESTAMP),
            ],
            indexes=[
                {"columns": ["token"], "name": "idx_sessions_token"},
                {"columns": ["user_id"], "name": "idx_sessions_user"},
                {"columns": ["status"], "name": "idx_sessions_status"},
                {"columns": ["expires_at"], "name": "idx_sessions_expires"},
            ]
        )

        login_logs_table = TableDef(
            name="login_logs",
            description="All login attempts log",
            columns=[
                ColumnDef(name="id", type=SQLType.SERIAL, primary_key=True, nullable=False),
                ColumnDef(name="user_id", type=SQLType.INTEGER, references="users.id", on_delete="SET NULL"),
                ColumnDef(name="email_attempted", type=SQLType.STRING, length=255, nullable=False),
                ColumnDef(name="status", type=SQLType.STRING, length=50, nullable=False,
                         check_constraint="status IN ('success', 'failed', 'suspicious', 'blocked')"),
                ColumnDef(name="ip_address", type=SQLType.INET),
                ColumnDef(name="device_info", type=SQLType.STRING, length=255),
                ColumnDef(name="browser", type=SQLType.STRING, length=255),
                ColumnDef(name="os_info", type=SQLType.STRING, length=255),
                ColumnDef(name="location", type=SQLType.STRING, length=255),
                ColumnDef(name="failure_reason", type=SQLType.STRING, length=255),
                ColumnDef(name="session_token", type=SQLType.STRING, length=500),
                ColumnDef(name="attempt_time", type=SQLType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
                ColumnDef(name="risk_score", type=SQLType.INTEGER, default=0,
                         check_constraint="risk_score BETWEEN 0 AND 100"),
            ],
            indexes=[
                {"columns": ["user_id"], "name": "idx_logs_user"},
                {"columns": ["email_attempted"], "name": "idx_logs_email"},
                {"columns": ["attempt_time"], "name": "idx_logs_time"},
                {"columns": ["ip_address"], "name": "idx_logs_ip"},
                {"columns": ["status"], "name": "idx_logs_status"},
            ]
        )

        return SchemaDef(
            version="2.2.0",
            tables=[users_table, sessions_table, login_logs_table]
        )

# ═════════════════════════════════════════════════════════════════
# AUTO-MIGRATE FUNCTIONS
# ═════════════════════════════════════════════════════════════════

def auto_migrate(description: str = "") -> Dict:
    engine = MigrationEngine()
    schema = SchemaRegistry.get_current_schema()
    return engine.execute_migration(schema, description)

def get_migration_status() -> Dict:
    engine = MigrationEngine()
    current = engine.get_current_schema_version()
    history = engine.get_migration_history(10)
    schema = SchemaRegistry.get_current_schema()
    return {
        "current_version": current["version"] if current else "none",
        "current_hash": current["schema_hash"] if current else "none",
        "target_version": schema.version,
        "target_hash": schema.to_hash(),
        "needs_update": (current["schema_hash"] if current else "") != schema.to_hash(),
        "recent_migrations": history,
        "tables_defined": [t.name for t in schema.tables]
    }

# ═════════════════════════════════════════════════════════════════
# FASTAPI ROUTES
# ═════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

migrate_router = APIRouter(prefix="/migrate", tags=["Auto-Migration"])

@migrate_router.post("/run")
async def run_migration(description: str = ""):
    result = auto_migrate(description)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result)
    return result

@migrate_router.get("/status")
async def migration_status():
    return get_migration_status()

@migrate_router.get("/history")
async def migration_history(limit: int = 50):
    engine = MigrationEngine()
    return {"migrations": engine.get_migration_history(limit)}

@migrate_router.post("/rollback/{migration_id}")
async def rollback(migration_id: int):
    engine = MigrationEngine()
    result = engine.rollback_migration(migration_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result)
    return result

@migrate_router.get("/preview")
async def preview_changes():
    engine = MigrationEngine()
    schema = SchemaRegistry.get_current_schema()
    changes = engine.detect_changes(schema)
    if not changes:
        return {"message": "No changes needed", "changes": []}
    sql, tables = engine.generate_migration_sql(changes)
    return {"changes_count": len(changes), "tables_affected": tables, "changes": changes, "sql_preview": sql}

@migrate_router.get("/schema")
async def get_schema_definition():
    schema = SchemaRegistry.get_current_schema()
    return {
        "version": schema.version,
        "hash": schema.to_hash(),
        "tables": [
            {
                "name": t.name,
                "description": t.description,
                "columns": [{"name": c.name, "type": c.type.value, "length": c.length, "nullable": c.nullable,
                            "default": c.default, "primary_key": c.primary_key, "unique": c.unique, "references": c.references}
                           for c in t.columns],
                "indexes": t.indexes
            }
            for t in schema.tables
        ]
    }

# Export
__all__ = ["MigrationEngine", "SchemaRegistry", "SchemaDef", "TableDef", "ColumnDef",
           "SQLType", "auto_migrate", "get_migration_status", "migrate_router"]
