import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path

from fastapi import HTTPException

DB_PATH = Path(__file__).resolve().parents[3] / "Data" / "pathai.db"


def _connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, "
        "password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, "
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP, "
        "FOREIGN KEY(user_id) REFERENCES users(id))"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS learner_profiles ("
        "user_id INTEGER PRIMARY KEY, goal TEXT NOT NULL, current_skills TEXT NOT NULL, "
        "level TEXT NOT NULL, learning_style TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, "
        "FOREIGN KEY(user_id) REFERENCES users(id))"
    )
    connection.commit()
    return connection


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$", 1)
    candidate = _hash_password(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
    return hmac.compare_digest(candidate, digest_hex)


def authenticate(email: str, password: str, create: bool = False) -> dict:
    normalized_email = email.strip().lower()
    connection = _connection()
    try:
        user = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
        if create:
            if user:
                raise HTTPException(status_code=409, detail="An account with this email already exists.")
            cursor = connection.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                (normalized_email, _hash_password(password)),
            )
            connection.commit()
            user = connection.execute(
                "SELECT id, email, password_hash FROM users WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        elif not user or not _verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        token = secrets.token_urlsafe(32)
        connection.execute("INSERT INTO sessions(token, user_id) VALUES (?, ?)", (token, user["id"]))
        connection.commit()
        return {"token": token, "email": user["email"]}
    finally:
        connection.close()


def get_user_from_token(token: str) -> dict:
    connection = _connection()
    try:
        user = connection.execute(
            "SELECT users.id, users.email FROM users JOIN sessions ON sessions.user_id = users.id "
            "WHERE sessions.token = ?",
            (token,),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Your session is invalid or expired.")
        return dict(user)
    finally:
        connection.close()


def save_profile(user_id: int, profile: dict):
    connection = _connection()
    try:
        import json
        connection.execute(
            "INSERT INTO learner_profiles(user_id, goal, current_skills, level, learning_style) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET goal=excluded.goal, "
            "current_skills=excluded.current_skills, level=excluded.level, "
            "learning_style=excluded.learning_style, updated_at=CURRENT_TIMESTAMP",
            (user_id, profile["goal"], json.dumps(profile["current_skills"]), profile["level"], profile["learning_style"]),
        )
        connection.commit()
        return profile
    finally:
        connection.close()