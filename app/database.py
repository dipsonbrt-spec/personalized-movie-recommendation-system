import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
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
"""

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

def create_user(username: str):
    username = username.strip()
    if not username:
        raise ValueError("Username is required")
    with get_connection() as conn:
        try:
            cur = conn.execute("INSERT INTO users(username) VALUES (?)", (username,))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Username already exists") from exc
        return cur.lastrowid

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
