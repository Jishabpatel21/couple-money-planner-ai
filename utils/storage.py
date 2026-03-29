from __future__ import annotations

import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from pathlib import Path


DB_PATH = Path("data/database.db")


def _hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(digest).decode()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = binascii.unhexlify(salt_hex.encode())
        expected = binascii.unhexlify(digest_hex.encode())
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL NOT NULL,
            monthly_contribution REAL NOT NULL,
            target_months INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Backward-compatible migration for older DBs.
    cur.execute("PRAGMA table_info(profiles)")
    profile_cols = [row[1] for row in cur.fetchall()]
    if "user_id" not in profile_cols:
        cur.execute("ALTER TABLE profiles ADD COLUMN user_id INTEGER")

    cur.execute("PRAGMA table_info(goals)")
    goal_cols = [row[1] for row in cur.fetchall()]
    if "user_id" not in goal_cols:
        cur.execute("ALTER TABLE goals ADD COLUMN user_id INTEGER")

    # Backward-compatible migration for legacy password reset schema.
    cur.execute("PRAGMA table_info(password_resets)")
    reset_cols = [row[1] for row in cur.fetchall()]

    if "user_id" not in reset_cols:
        cur.execute("ALTER TABLE password_resets ADD COLUMN user_id INTEGER")

    if "token_hash" not in reset_cols:
        cur.execute("ALTER TABLE password_resets ADD COLUMN token_hash TEXT")
        if "token" in reset_cols:
            cur.execute(
                "UPDATE password_resets SET token_hash = token WHERE token_hash IS NULL OR token_hash = ''"
            )

    if "expires_at" not in reset_cols:
        cur.execute("ALTER TABLE password_resets ADD COLUMN expires_at TEXT")

    if "used_at" not in reset_cols:
        cur.execute("ALTER TABLE password_resets ADD COLUMN used_at TEXT")

    conn.commit()
    conn.close()


def request_password_reset(email: str, ttl_minutes: int = 15) -> tuple[bool, str, str | None]:
    email = email.strip().lower()
    if not email:
        return False, "Email is required.", None

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "No account found for this email.", None

    user_id = int(row[0])
    token = secrets.token_urlsafe(24)
    token_hash = _hash_reset_token(token)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat()

    cur.execute("PRAGMA table_info(password_resets)")
    reset_cols = {row[1] for row in cur.fetchall()}

    insert_cols = ["user_id", "token_hash", "expires_at"]
    insert_vals: list[object] = [user_id, token_hash, expires_at]

    # Legacy schema compatibility.
    if "reset_code" in reset_cols:
        insert_cols.append("reset_code")
        insert_vals.append(token_hash)
    if "used" in reset_cols:
        insert_cols.append("used")
        insert_vals.append(0)

    placeholders = ", ".join(["?"] * len(insert_cols))
    columns_sql = ", ".join(insert_cols)
    cur.execute(
        f"INSERT INTO password_resets ({columns_sql}) VALUES ({placeholders})",
        tuple(insert_vals),
    )
    conn.commit()
    conn.close()
    return True, f"Reset token created. It expires in {ttl_minutes} minutes.", token


def reset_password_with_token(email: str, token: str, new_password: str) -> tuple[bool, str]:
    email = email.strip().lower()
    token = token.strip()
    if not email or not token or not new_password:
        return False, "Email, reset token, and new password are required."
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters."

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    user_row = cur.fetchone()
    if not user_row:
        conn.close()
        return False, "No account found for this email."

    user_id = int(user_row[0])
    token_hash = _hash_reset_token(token)
    now = datetime.now(timezone.utc)

    cur.execute("PRAGMA table_info(password_resets)")
    reset_cols = {row[1] for row in cur.fetchall()}

    token_hash_sel = "token_hash" if "token_hash" in reset_cols else "NULL AS token_hash"
    reset_code_sel = "reset_code" if "reset_code" in reset_cols else "NULL AS reset_code"
    expires_sel = "expires_at" if "expires_at" in reset_cols else "NULL AS expires_at"
    created_sel = "created_at" if "created_at" in reset_cols else "NULL AS created_at"

    where_clauses = ["user_id = ?"]
    if "used_at" in reset_cols:
        where_clauses.append("used_at IS NULL")
    if "used" in reset_cols:
        where_clauses.append("(used IS NULL OR used = 0)")
    where_sql = " AND ".join(where_clauses)

    cur.execute(
        f"""
        SELECT id, {token_hash_sel}, {reset_code_sel}, {expires_sel}, {created_sel}
        FROM password_resets
        WHERE {where_sql}
        ORDER BY id DESC
        """,
        (user_id,),
    )
    token_rows = cur.fetchall()

    matched_reset_id = None
    for reset_id, stored_hash, reset_code, expires_at, created_at in token_rows:
        expires_dt = None
        try:
            if expires_at:
                expires_dt = datetime.fromisoformat(str(expires_at))
            elif created_at:
                created_dt = datetime.fromisoformat(str(created_at))
                expires_dt = created_dt + timedelta(minutes=15)
        except ValueError:
            continue
        if expires_dt is None:
            continue
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if expires_dt < now:
            continue

        is_match = False
        if stored_hash and hmac.compare_digest(str(stored_hash), token_hash):
            is_match = True
        elif reset_code and (
            hmac.compare_digest(str(reset_code), token_hash) or hmac.compare_digest(str(reset_code), token)
        ):
            is_match = True

        if is_match:
            matched_reset_id = int(reset_id)
            break

    if matched_reset_id is None:
        conn.close()
        return False, "Invalid or expired reset token."

    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (_hash_password(new_password), user_id))
    update_sets = []
    if "used_at" in reset_cols:
        update_sets.append("used_at = CURRENT_TIMESTAMP")
    if "used" in reset_cols:
        update_sets.append("used = 1")
    if update_sets:
        cur.execute(
            f"UPDATE password_resets SET {', '.join(update_sets)} WHERE id = ?",
            (matched_reset_id,),
        )
    conn.commit()
    conn.close()
    return True, "Password reset successful. You can now login with your new password."


def create_user(name: str, email: str, password: str, initial_profile: dict | None = None) -> tuple[bool, str]:
    name = name.strip()
    email = email.strip().lower()
    if not name or not email or not password:
        return False, "Name, email, and password are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, _hash_password(password)),
        )

        # Optionally create an initial profile snapshot at signup time.
        if initial_profile is not None:
            user_id = int(cur.lastrowid)
            cur.execute(
                "INSERT INTO profiles (user_id, payload) VALUES (?, ?)",
                (user_id, json.dumps(initial_profile)),
            )

        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "Email already exists."
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> dict | None:
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None
    user_id, name, user_email, password_hash = row
    if not _verify_password(password, password_hash):
        return None
    return {"id": int(user_id), "name": str(name), "email": str(user_email)}


def count_users() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    conn.close()
    return int(total)


def list_db_tables() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    tables = [str(row[0]) for row in cur.fetchall()]
    conn.close()
    return tables


def fetch_table_rows(table_name: str, limit: int = 100) -> tuple[list[str], list[tuple]]:
    tables = set(list_db_tables())
    if table_name not in tables:
        return [], []

    safe_limit = max(1, min(int(limit), 500))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [str(row[1]) for row in cur.fetchall()]
    if not columns:
        conn.close()
        return [], []

    # rowid ordering works for normal SQLite tables and keeps latest rows first.
    cur.execute(f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT ?", (safe_limit,))
    rows = cur.fetchall()
    conn.close()
    return columns, rows


def get_user_overview(user_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM profiles WHERE user_id = ?", (user_id,))
    profile_count = int(cur.fetchone()[0])

    cur.execute("SELECT COUNT(*) FROM goals WHERE user_id = ?", (user_id,))
    goal_count = int(cur.fetchone()[0])

    conn.close()
    return {"profiles": profile_count, "goals": goal_count}


def delete_user_and_data(user_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM goals WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def save_profile(data: dict, user_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO profiles (user_id, payload) VALUES (?, ?)", (user_id, json.dumps(data)))
    conn.commit()
    conn.close()


def load_latest_profile(user_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT payload FROM profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row[0])


def add_goal(
    name: str,
    target_amount: float,
    current_amount: float,
    monthly_contribution: float,
    target_months: int,
    user_id: int,
) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO goals (user_id, name, target_amount, current_amount, monthly_contribution, target_months)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, name, target_amount, current_amount, monthly_contribution, target_months),
    )
    conn.commit()
    conn.close()


def delete_goal(goal_id: int, user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def list_goals(user_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, target_amount, current_amount, monthly_contribution, target_months
        FROM goals
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()

    goals = []
    for row in rows:
        goal_id, name, target, current, monthly, months = row
        progress = 0.0 if target <= 0 else min(100.0, (current / target) * 100)
        projected = current + monthly * months
        goals.append(
            {
                "id": goal_id,
                "name": name,
                "target_amount": float(target),
                "current_amount": float(current),
                "monthly_contribution": float(monthly),
                "target_months": int(months),
                "progress": float(progress),
                "projected_amount": float(projected),
            }
        )
    return goals
