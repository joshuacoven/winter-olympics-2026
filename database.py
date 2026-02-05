"""
Database operations for the Winter Olympics Prediction Game.

Uses libsql for Turso (remote) or local SQLite fallback.
Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN env vars for Turso.
"""

import logging
import os
import sqlite3
import string
import random
from pathlib import Path

logger = logging.getLogger(__name__)

# Database file path (used for local SQLite fallback)
DB_PATH = Path(__file__).parent / "olympics_pools.db"

# Turso connection settings
TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")


_using_turso = bool(TURSO_URL and TURSO_TOKEN)


def _row_to_dict(cursor, row):
    """Convert a raw row tuple to a dict using cursor.description."""
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def _rows_to_dicts(cursor, rows):
    """Convert a list of raw row tuples to dicts."""
    if not rows:
        return []
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def fetchone_dict(cursor):
    """Fetch one row as a dict (works with both SQLite and libsql)."""
    row = cursor.fetchone()
    if _using_turso:
        return _row_to_dict(cursor, row)
    return row  # sqlite3.Row already supports row["col"]


def fetchall_dicts(cursor):
    """Fetch all rows as dicts (works with both SQLite and libsql)."""
    rows = cursor.fetchall()
    if _using_turso:
        return _rows_to_dicts(cursor, rows)
    return rows  # sqlite3.Row already supports row["col"]


_cached_conn = None


def get_connection():
    """Get a database connection. Reuses a cached connection when possible."""
    global _cached_conn
    if _cached_conn is not None:
        try:
            _cached_conn.execute("SELECT 1")
            return _cached_conn
        except Exception:
            _cached_conn = None

    if _using_turso:
        import libsql_experimental as libsql
        conn = libsql.connect("local.db", sync_url=TURSO_URL, auth_token=TURSO_TOKEN)
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout = 5000")

    _cached_conn = conn
    return conn


def _sync_if_turso(conn):
    """Sync embedded replica to Turso remote if using Turso."""
    if TURSO_URL and TURSO_TOKEN:
        try:
            conn.sync()
        except Exception:
            logger.warning("Turso sync failed", exc_info=True)


_db_initialized = False


def init_db():
    """Initialize the database with required tables. Only runs once."""
    global _db_initialized
    if _db_initialized:
        return
    _db_initialized = True

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                pin TEXT
            )
        """)

        # Add pin column if it doesn't exist (migration for existing DBs)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN pin TEXT")
        except (sqlite3.OperationalError, Exception):
            pass  # Column already exists

        # Create pools table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pools (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_by TEXT NOT NULL
            )
        """)

        # Create pool_members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pool_members (
                pool_code TEXT NOT NULL,
                username TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                FOREIGN KEY (pool_code) REFERENCES pools(code),
                FOREIGN KEY (username) REFERENCES users(username),
                UNIQUE(pool_code, username)
            )
        """)

        # Create prediction_sets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username),
                UNIQUE(username, name)
            )
        """)

        # Create pool_prediction_set_assignments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pool_prediction_set_assignments (
                pool_code TEXT NOT NULL,
                username TEXT NOT NULL,
                prediction_set_id INTEGER NOT NULL,
                FOREIGN KEY (pool_code) REFERENCES pools(code),
                FOREIGN KEY (username) REFERENCES users(username),
                FOREIGN KEY (prediction_set_id) REFERENCES prediction_sets(id),
                UNIQUE(pool_code, username)
            )
        """)

        # Create predictions table (uses prediction_set_id and category_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_set_id INTEGER NOT NULL,
                category_id TEXT NOT NULL,
                country TEXT NOT NULL,
                FOREIGN KEY (prediction_set_id) REFERENCES prediction_sets(id),
                UNIQUE(prediction_set_id, category_id)
            )
        """)

        # Create category_results table (for tracking actual results)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id TEXT NOT NULL UNIQUE,
                winning_country TEXT NOT NULL
            )
        """)

        # Keep old tables for backward compatibility during migration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pool_code TEXT NOT NULL,
                user_name TEXT NOT NULL,
                event_id TEXT NOT NULL,
                country TEXT NOT NULL,
                FOREIGN KEY (pool_code) REFERENCES pools(code),
                UNIQUE(pool_code, user_name, event_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pool_code TEXT NOT NULL,
                event_id TEXT NOT NULL,
                country TEXT NOT NULL,
                FOREIGN KEY (pool_code) REFERENCES pools(code),
                UNIQUE(pool_code, event_id)
            )
        """)

        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass

    # Run migration for existing data
    migrate_existing_data()


def migrate_existing_data():
    """Migrate existing prediction data to users and pool_members tables."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Skip migration if old predictions table is empty (nothing to migrate)
        cursor.execute("SELECT COUNT(*) FROM predictions")
        count_row = cursor.fetchone()
        count = count_row[0] if isinstance(count_row, tuple) else count_row["COUNT(*)"] if count_row else 0
        if count == 0:
            return

        # Get all unique usernames from predictions
        cursor.execute("SELECT DISTINCT user_name FROM predictions")
        prediction_users = [row["user_name"] for row in fetchall_dicts(cursor)]

        # Get all pool creators
        cursor.execute("SELECT DISTINCT created_by FROM pools")
        creator_users = [row["created_by"] for row in fetchall_dicts(cursor)]

        # Create users for all unique usernames
        all_users = set(prediction_users + creator_users)
        for username in all_users:
            cursor.execute(
                "INSERT OR IGNORE INTO users (username) VALUES (?)",
                (username,)
            )

        # Add pool creators as admin members
        cursor.execute("SELECT code, created_by FROM pools")
        pools = fetchall_dicts(cursor)
        for pool in pools:
            cursor.execute(
                "INSERT OR IGNORE INTO pool_members (pool_code, username, is_admin) VALUES (?, ?, 1)",
                (pool["code"], pool["created_by"])
            )

        # Add users who made predictions as pool members
        cursor.execute("SELECT DISTINCT pool_code, user_name FROM predictions")
        memberships = fetchall_dicts(cursor)
        for membership in memberships:
            cursor.execute(
                "INSERT OR IGNORE INTO pool_members (pool_code, username, is_admin) VALUES (?, ?, 0)",
                (membership["pool_code"], membership["user_name"])
            )

        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


def create_user(username: str, pin: str) -> bool:
    """Create a new user with a PIN. Returns True if created, False if already exists."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, pin) VALUES (?, ?)", (username, pin))
            conn.commit()
            _sync_if_turso(conn)
            return True
        except (sqlite3.IntegrityError, Exception) as e:
            if "UNIQUE constraint" not in str(e) and "IntegrityError" not in type(e).__name__:
                raise
            return False
    finally:
        pass


def user_exists(username: str) -> bool:
    """Check if a user exists."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        return cursor.fetchone() is not None
    finally:
        pass


def verify_pin(username: str, pin: str) -> bool:
    """Verify a user's PIN. Returns True if correct."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT pin FROM users WHERE username = ?", (username,))
        row = fetchone_dict(cursor)
        if not row:
            return False
        return row["pin"] == pin
    finally:
        pass


def get_user_pools(username: str) -> list[dict]:
    """Get all pools a user belongs to."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.code, p.name, p.created_by, pm.is_admin
            FROM pools p
            JOIN pool_members pm ON p.code = pm.pool_code
            WHERE pm.username = ?
            ORDER BY p.name
        """, (username,))
        rows = fetchall_dicts(cursor)
        return [
            {
                "code": row["code"],
                "name": row["name"],
                "created_by": row["created_by"],
                "is_admin": bool(row["is_admin"])
            }
            for row in rows
        ]
    finally:
        pass


def add_pool_member(pool_code: str, username: str, is_admin: bool = False):
    """Add a user to a pool."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO pool_members (pool_code, username, is_admin) VALUES (?, ?, ?)",
            (pool_code, username, int(is_admin))
        )
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


def is_pool_admin(pool_code: str, username: str) -> bool:
    """Check if a user is an admin of a pool."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_admin FROM pool_members WHERE pool_code = ? AND username = ?",
            (pool_code, username)
        )
        row = fetchone_dict(cursor)
        return bool(row["is_admin"]) if row else False
    finally:
        pass


def generate_pool_code() -> str:
    """Generate a unique 6-character pool code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if not pool_exists(code):
            return code


def pool_exists(code: str) -> bool:
    """Check if a pool with the given code exists."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pools WHERE code = ?", (code,))
        return cursor.fetchone() is not None
    finally:
        pass


def pool_name_exists(name: str) -> bool:
    """Check if a pool with the given name exists (case-insensitive)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pools WHERE LOWER(name) = LOWER(?)", (name,))
        return cursor.fetchone() is not None
    finally:
        pass


def create_pool(name: str, created_by: str) -> str | None:
    """
    Create a new pool and return its name.
    Returns None if a pool with that name already exists.
    Also adds the creator as an admin member.
    """
    if pool_name_exists(name):
        return None
    code = generate_pool_code()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pools (code, name, created_by) VALUES (?, ?, ?)",
            (code, name, created_by)
        )
        # Add creator as admin member
        cursor.execute(
            "INSERT INTO pool_members (pool_code, username, is_admin) VALUES (?, ?, 1)",
            (code, created_by)
        )
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass
    return name


def get_pool(code: str) -> dict | None:
    """
    Get pool info by code.
    Returns dict with code, name, created_by or None if not found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT code, name, created_by FROM pools WHERE code = ?", (code,))
        row = fetchone_dict(cursor)
        if row:
            return {"code": row["code"], "name": row["name"], "created_by": row["created_by"]}
        return None
    finally:
        pass


def get_pool_by_name(name: str) -> dict | None:
    """
    Get pool info by name (case-insensitive).
    Returns dict with code, name, created_by or None if not found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT code, name, created_by FROM pools WHERE LOWER(name) = LOWER(?)", (name,))
        row = fetchone_dict(cursor)
        if row:
            return {"code": row["code"], "name": row["name"], "created_by": row["created_by"]}
        return None
    finally:
        pass


def save_prediction(pool_code: str, user_name: str, event_id: str, country: str):
    """
    Save or update a user's prediction for an event.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions (pool_code, user_name, event_id, country)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(pool_code, user_name, event_id)
            DO UPDATE SET country = excluded.country
        """, (pool_code, user_name, event_id, country))
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


def get_user_predictions(pool_code: str, user_name: str) -> dict[str, str]:
    """
    Get all predictions for a user in a pool.
    Returns dict mapping event_id to country.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_id, country FROM predictions WHERE pool_code = ? AND user_name = ?",
            (pool_code, user_name)
        )
        rows = fetchall_dicts(cursor)
        return {row["event_id"]: row["country"] for row in rows}
    finally:
        pass


def get_all_predictions(pool_code: str) -> dict[str, dict[str, str]]:
    """
    Get all predictions for all users in a pool.
    Returns dict mapping user_name to dict of event_id -> country.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_name, event_id, country FROM predictions WHERE pool_code = ?",
            (pool_code,)
        )
        rows = fetchall_dicts(cursor)
        predictions = {}
        for row in rows:
            user = row["user_name"]
            if user not in predictions:
                predictions[user] = {}
            predictions[user][row["event_id"]] = row["country"]
        return predictions
    finally:
        pass


def get_pool_participants(pool_code: str) -> list[str]:
    """Get list of all participants who have made predictions in a pool."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT user_name FROM predictions WHERE pool_code = ?",
            (pool_code,)
        )
        rows = fetchall_dicts(cursor)
        return [row["user_name"] for row in rows]
    finally:
        pass


def save_result(pool_code: str, event_id: str, country: str):
    """
    Save or update the actual result for an event.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO results (pool_code, event_id, country)
            VALUES (?, ?, ?)
            ON CONFLICT(pool_code, event_id)
            DO UPDATE SET country = excluded.country
        """, (pool_code, event_id, country))
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


def get_results(pool_code: str) -> dict[str, str]:
    """
    Get all results for a pool.
    Returns dict mapping event_id to winning country.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_id, country FROM results WHERE pool_code = ?",
            (pool_code,)
        )
        rows = fetchall_dicts(cursor)
        return {row["event_id"]: row["country"] for row in rows}
    finally:
        pass


def clear_result(pool_code: str, event_id: str):
    """Remove a result entry (in case of correction)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM results WHERE pool_code = ? AND event_id = ?",
            (pool_code, event_id)
        )
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


# ============== NEW PREDICTION SET FUNCTIONS ==============

def create_prediction_set(username: str, name: str) -> int | None:
    """Create a new prediction set. Returns the set ID or None if name exists."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO prediction_sets (username, name) VALUES (?, ?)",
                (username, name)
            )
            conn.commit()
            _sync_if_turso(conn)
            return cursor.lastrowid
        except (sqlite3.IntegrityError, Exception) as e:
            if "UNIQUE constraint" not in str(e) and "IntegrityError" not in type(e).__name__:
                raise
            return None
    finally:
        pass


def get_user_prediction_sets(username: str) -> list[dict]:
    """Get all prediction sets for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, created_at FROM prediction_sets WHERE username = ? ORDER BY name",
            (username,)
        )
        rows = fetchall_dicts(cursor)
        return [
            {"id": row["id"], "name": row["name"], "created_at": row["created_at"]}
            for row in rows
        ]
    finally:
        pass


def get_prediction_set(set_id: int) -> dict | None:
    """Get a specific prediction set by ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, username, created_at FROM prediction_sets WHERE id = ?",
            (set_id,)
        )
        row = fetchone_dict(cursor)
        if row:
            return {
                "id": row["id"],
                "name": row["name"],
                "username": row["username"],
                "created_at": row["created_at"]
            }
        return None
    finally:
        pass


def delete_prediction_set(set_id: int):
    """Delete a prediction set and all its predictions."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Delete predictions first
        cursor.execute("DELETE FROM predictions_v2 WHERE prediction_set_id = ?", (set_id,))
        # Delete assignments
        cursor.execute("DELETE FROM pool_prediction_set_assignments WHERE prediction_set_id = ?", (set_id,))
        # Delete the set
        cursor.execute("DELETE FROM prediction_sets WHERE id = ?", (set_id,))
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


def assign_prediction_set_to_pool(pool_code: str, username: str, prediction_set_id: int):
    """Assign a prediction set to a pool for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pool_prediction_set_assignments (pool_code, username, prediction_set_id)
            VALUES (?, ?, ?)
            ON CONFLICT(pool_code, username)
            DO UPDATE SET prediction_set_id = excluded.prediction_set_id
        """, (pool_code, username, prediction_set_id))
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


def get_pool_assignment(pool_code: str, username: str) -> int | None:
    """Get which prediction set a user is using for a pool."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT prediction_set_id FROM pool_prediction_set_assignments WHERE pool_code = ? AND username = ?",
            (pool_code, username)
        )
        row = fetchone_dict(cursor)
        return row["prediction_set_id"] if row else None
    finally:
        pass


def get_pool_assignments_for_pool(pool_code: str) -> dict[str, int]:
    """Get all prediction set assignments for a pool. Returns dict of username -> set_id."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, prediction_set_id FROM pool_prediction_set_assignments WHERE pool_code = ?",
            (pool_code,)
        )
        rows = fetchall_dicts(cursor)
        return {row["username"]: row["prediction_set_id"] for row in rows}
    finally:
        pass


def save_set_prediction(prediction_set_id: int, category_id: str, country: str):
    """Save or update a prediction in a prediction set."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions_v2 (prediction_set_id, category_id, country)
            VALUES (?, ?, ?)
            ON CONFLICT(prediction_set_id, category_id)
            DO UPDATE SET country = excluded.country
        """, (prediction_set_id, category_id, country))
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


def get_predictions_for_set(prediction_set_id: int) -> dict[str, str]:
    """Get all predictions in a prediction set. Returns dict of category_id -> country."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT category_id, country FROM predictions_v2 WHERE prediction_set_id = ?",
            (prediction_set_id,)
        )
        rows = fetchall_dicts(cursor)
        return {row["category_id"]: row["country"] for row in rows}
    finally:
        pass


def get_category_results() -> dict[str, list[str]]:
    """Get all category results. Returns dict of category_id -> list of winning countries.

    Supports ties: multiple winners are stored as comma-separated values in the DB.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT category_id, winning_country FROM category_results")
        rows = fetchall_dicts(cursor)
        return {
            row["category_id"]: [c.strip() for c in row["winning_country"].split(",")]
            for row in rows
        }
    finally:
        pass


def save_category_result(category_id: str, winning_country: str):
    """Save or update a category result."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO category_results (category_id, winning_country)
            VALUES (?, ?)
            ON CONFLICT(category_id)
            DO UPDATE SET winning_country = excluded.winning_country
        """, (category_id, winning_country))
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


# ============== ADMIN POOL MANAGEMENT FUNCTIONS ==============

def get_all_pools() -> list[dict]:
    """Get all pools."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT code, name, created_by FROM pools ORDER BY name")
        rows = fetchall_dicts(cursor)
        return [
            {"code": row["code"], "name": row["name"], "created_by": row["created_by"]}
            for row in rows
        ]
    finally:
        pass


def get_all_users_with_prediction_sets() -> list[dict]:
    """Get all users who have prediction sets."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username, ps.id, ps.name
            FROM users u
            JOIN prediction_sets ps ON u.username = ps.username
            ORDER BY u.username, ps.name
        """)
        rows = fetchall_dicts(cursor)
        # Group by username
        users = {}
        for row in rows:
            if row["username"] not in users:
                users[row["username"]] = {"username": row["username"], "sets": []}
            users[row["username"]]["sets"].append({"id": row["id"], "name": row["name"]})
        return list(users.values())
    finally:
        pass


def get_users_not_in_pool(pool_code: str) -> list[dict]:
    """Get users with prediction sets who are NOT in the specified pool."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT u.username
            FROM users u
            JOIN prediction_sets ps ON u.username = ps.username
            WHERE u.username NOT IN (
                SELECT username FROM pool_members WHERE pool_code = ?
            )
            ORDER BY u.username
        """, (pool_code,))
        usernames = [row["username"] for row in fetchall_dicts(cursor)]

        # Get their prediction sets
        all_users = get_all_users_with_prediction_sets()
        return [u for u in all_users if u["username"] in usernames]
    finally:
        pass


def admin_add_user_to_pool(pool_code: str, username: str, prediction_set_id: int):
    """Add user to pool and assign their prediction set."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Add to pool_members (ignore if already exists)
        cursor.execute(
            "INSERT OR IGNORE INTO pool_members (pool_code, username, is_admin) VALUES (?, ?, 0)",
            (pool_code, username)
        )
        # Assign prediction set
        cursor.execute("""
            INSERT INTO pool_prediction_set_assignments (pool_code, username, prediction_set_id)
            VALUES (?, ?, ?)
            ON CONFLICT(pool_code, username) DO UPDATE SET prediction_set_id = excluded.prediction_set_id
        """, (pool_code, username, prediction_set_id))
        conn.commit()
        _sync_if_turso(conn)
    finally:
        pass


def get_pool_members_with_assignments(pool_code: str) -> list[dict]:
    """Get all pool members with their prediction set assignments."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pm.username, pm.is_admin, psa.prediction_set_id, ps.name as set_name
            FROM pool_members pm
            LEFT JOIN pool_prediction_set_assignments psa
                ON pm.pool_code = psa.pool_code AND pm.username = psa.username
            LEFT JOIN prediction_sets ps ON psa.prediction_set_id = ps.id
            WHERE pm.pool_code = ?
            ORDER BY pm.username
        """, (pool_code,))
        rows = fetchall_dicts(cursor)
        return [
            {
                "username": row["username"],
                "is_admin": bool(row["is_admin"]),
                "prediction_set_id": row["prediction_set_id"],
                "set_name": row["set_name"]
            }
            for row in rows
        ]
    finally:
        pass


# Initialize database when module is imported
init_db()
