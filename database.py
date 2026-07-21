"""
Rafeeq Kernel - Database Module
Handles PostgreSQL connection and ORM operations
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime
import bcrypt
import secrets

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dtr_no_user:GRtFA4nVLhnELSi8xTookZyKasr8XoME@dpg-d9dlnlv7f7vs738ugbe0-a/dtr_no")

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Initialize database tables"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table - FIXED with avatar column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              SERIAL PRIMARY KEY,
                email           VARCHAR(255) UNIQUE NOT NULL,
                username        VARCHAR(100) UNIQUE,
                password_hash   VARCHAR(255) NOT NULL,
                full_name       VARCHAR(255),
                avatar          VARCHAR(500) DEFAULT NULL,
                bio             TEXT DEFAULT NULL,
                role            VARCHAR(50) DEFAULT 'user',
                status          VARCHAR(50) DEFAULT 'active',
                email_verified  BOOLEAN DEFAULT FALSE,
                last_login      TIMESTAMP DEFAULT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                token           VARCHAR(500) UNIQUE NOT NULL,
                ip_address      VARCHAR(45) DEFAULT NULL,
                user_agent      TEXT DEFAULT NULL,
                expires_at      TIMESTAMP NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Activities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
                action          VARCHAR(100) NOT NULL,
                description     TEXT DEFAULT NULL,
                metadata        JSONB DEFAULT NULL,
                ip_address      VARCHAR(45) DEFAULT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_user ON activities(user_id)")

        # Insert default admin if not exists
        cursor.execute("SELECT id FROM users WHERE email = 'admin@rafeeq.ai'")
        if not cursor.fetchone():
            hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            cursor.execute("""
                INSERT INTO users (email, username, password_hash, full_name, role, email_verified, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ("admin@rafeeq.ai", "admin", hashed, "System Administrator", "admin", True, "active"))

        conn.commit()
        print("✅ Database initialized successfully")
        return True

# User Model Operations
class UserModel:
    @staticmethod
    def create(email, password, username=None, full_name=None, avatar=None):
        """Create new user"""
        with get_db() as conn:
            cursor = conn.cursor()
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            try:
                cursor.execute("""
                    INSERT INTO users (email, username, password_hash, full_name, avatar, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, email, username, full_name, avatar, role, status, created_at
                """, (email, username, hashed, full_name, avatar, "active"))
                return cursor.fetchone()
            except psycopg2.IntegrityError:
                return None

    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()

    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()

    @staticmethod
    def verify_password(email, password):
        """Verify user password"""
        user = UserModel.get_by_email(email)
        if not user:
            return None
        if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return user
        return None

    @staticmethod
    def update_last_login(user_id):
        """Update last login timestamp"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_login = %s WHERE id = %s", (datetime.now(), user_id))

    @staticmethod
    def update_avatar(user_id, avatar_url):
        """Update user avatar"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET avatar = %s WHERE id = %s", (avatar_url, user_id))

    @staticmethod
    def count():
        """Count total users"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            return cursor.fetchone()["count"]

# Session Model Operations
class SessionModel:
    @staticmethod
    def create(user_id, ip_address=None, user_agent=None, expires_hours=24):
        """Create new session"""
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + __import__("datetime").timedelta(hours=expires_hours)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (user_id, token, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, token, expires_at
            """, (user_id, token, ip_address, user_agent, expires))
            return cursor.fetchone()

    @staticmethod
    def get_by_token(token):
        """Get session by token"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, u.email, u.username, u.full_name, u.avatar, u.role 
                FROM sessions s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.token = %s AND s.expires_at > %s
            """, (token, datetime.now()))
            return cursor.fetchone()

    @staticmethod
    def delete_by_token(token):
        """Delete session"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE token = %s", (token,))

    @staticmethod
    def count():
        """Count active sessions"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE expires_at > %s", (datetime.now(),))
            return cursor.fetchone()["count"]

# Activity Model Operations
class ActivityModel:
    @staticmethod
    def log(user_id, action, description=None, metadata=None, ip_address=None):
        """Log activity"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO activities (user_id, action, description, metadata, ip_address)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, action, description, json.dumps(metadata) if metadata else None, ip_address))

    @staticmethod
    def get_recent(limit=50):
        """Get recent activities"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, u.username, u.avatar 
                FROM activities a 
                JOIN users u ON a.user_id = u.id 
                ORDER BY a.created_at DESC 
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()

    @staticmethod
    def count():
        """Count total activities"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM activities")
            return cursor.fetchone()["count"]

# System Stats
def get_system_stats():
    """Get system statistics"""
    return {
        "users": UserModel.count(),
        "sessions": SessionModel.count(),
        "activities": ActivityModel.count(),
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }
