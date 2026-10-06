import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager
from .config import DB_PATH, MOVIES_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    rating REAL NOT NULL CHECK(rating >= 1 AND rating <= 5),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, movie_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER NOT NULL DEFAULT 0,
    genres TEXT NOT NULL DEFAULT 'Unknown',
    director TEXT NOT NULL DEFAULT '',
    cast TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '',
    overview TEXT NOT NULL DEFAULT '',
    runtime INTEGER NOT NULL DEFAULT 0
);
"""

PBKDF2_ITERATIONS = 200_000
MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 6


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
        if "password_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        _seed_movies(conn)


# ---------- movies ----------
def _text(value):
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value).strip()


def _int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _seed_movies(conn):
    """On first run, load the bundled movies.csv (keeping its ids so ratings stay valid)."""
    if conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0] > 0 or not MOVIES_PATH.exists():
        return
    import pandas as pd
    df = pd.read_csv(MOVIES_PATH)
    for rec in df.to_dict("records"):
        conn.execute(
            "INSERT INTO movies(id, title, year, genres, director, cast, keywords, overview, runtime) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (_int(rec["id"]), _text(rec["title"]), _int(rec.get("year")),
             _text(rec.get("genres")) or "Unknown", _text(rec.get("director")),
             _text(rec.get("cast")), _text(rec.get("keywords")),
             _text(rec.get("overview")), _int(rec.get("runtime"))),
        )


def get_all_movies():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM movies ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def add_movies(records):
    """Insert movies from uploaded CSV rows. Returns (added, skipped).
    Duplicates (same title + year, case-insensitive) and rows without a title are skipped."""
    added = skipped = 0
    with get_connection() as conn:
        existing = {(r["title"].strip().lower(), r["year"])
                    for r in conn.execute("SELECT title, year FROM movies")}
        for rec in records:
            title = _text(rec.get("title"))
            year = _int(rec.get("year"))
            if not title or (title.lower(), year) in existing:
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO movies(title, year, genres, director, cast, keywords, overview, runtime) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (title, year, _text(rec.get("genres")) or "Unknown", _text(rec.get("director")),
                 _text(rec.get("cast")), _text(rec.get("keywords")),
                 _text(rec.get("overview")), _int(rec.get("runtime"))),
            )
            existing.add((title.lower(), year))
            added += 1
    return added, skipped

# ---------- password helpers ----------
def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


# ---------- users ----------
def create_user(username: str, password: str):
    username = (username or "").strip()
    password = password or ""
    if len(username) < MIN_USERNAME_LENGTH:
        raise ValueError(f"Username must be at least {MIN_USERNAME_LENGTH} characters")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    with get_connection() as conn:
        # Case-insensitive uniqueness ("Dipson" and "dipson" are the same user)
        exists = conn.execute(
            "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?)", (username,)
        ).fetchone()
        if exists:
            raise ValueError("Username already exists. Please log in instead.")
        try:
            cur = conn.execute(
                "INSERT INTO users(username, password_hash) VALUES (?, ?)",
                (username, _hash_password(password)),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Username already exists. Please log in instead.") from exc
        return cur.lastrowid


def authenticate_user(username: str, password: str):
    """Return {'id', 'username'} if credentials are valid, else raise ValueError."""
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        raise ValueError("Enter your username and password")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE LOWER(username) = LOWER(?)",
            (username,),
        ).fetchone()
        if not row:
            raise ValueError("Invalid username or password")

        # Legacy account created before passwords existed: first login sets the password.
        if row["password_hash"] is None:
            if len(password) < MIN_PASSWORD_LENGTH:
                raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (_hash_password(password), row["id"]),
            )
            return {"id": row["id"], "username": row["username"]}

        if not _verify_password(password, row["password_hash"]):
            raise ValueError("Invalid username or password")
        return {"id": row["id"], "username": row["username"]}


def get_user(user_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def upsert_rating(user_id: int, movie_id: int, rating: float):
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
            raise ValueError("User not found")
        conn.execute("""
            INSERT INTO ratings(user_id, movie_id, rating) VALUES (?, ?, ?)
            ON CONFLICT(user_id, movie_id) DO UPDATE SET rating=excluded.rating, created_at=CURRENT_TIMESTAMP
        """, (user_id, movie_id, rating))


def get_ratings(user_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT movie_id, rating, created_at FROM ratings WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")