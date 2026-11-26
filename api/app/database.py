import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_FILE = Path(os.getenv("DATABASE_URL", "sqlite:////data/app.db").replace("sqlite:///", ""))


def _connect() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db = _connect()
    try:
        yield db
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'info',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS model_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                calls INTEGER NOT NULL DEFAULT 0,
                tokens INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                key_prefix TEXT NOT NULL,
                last_used_at TEXT,
                expires_at TEXT,
                revoked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS wallets (
                user_id INTEGER PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_after REAL NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                reference TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                api_key_id INTEGER,
                model_name TEXT NOT NULL,
                endpoint TEXT NOT NULL DEFAULT 'chat.completions',
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                cost REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'success',
                latency_ms INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(api_key_id) REFERENCES api_keys(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key TEXT NOT NULL DEFAULT '',
                model_mapping TEXT NOT NULL DEFAULT '{}',
                group_name TEXT NOT NULL DEFAULT 'default',
                weight REAL NOT NULL DEFAULT 1,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS model_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                weight REAL NOT NULL DEFAULT 1,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
            );
            """
        )
        count = db.execute("SELECT COUNT(*) AS count FROM notices").fetchone()["count"]
        if count == 0:
            db.executemany(
                "INSERT INTO notices(title, content, level) VALUES (?, ?, ?)",
                [
                    ("欢迎使用 CODEFARMER", "统一 API 网关已上线，注册后即可创建访问密钥。", "info"),
                    ("价格数据同步", "模型价格每 30 分钟从公开接口同步一次。", "success"),
                ],
            )
        db.execute(
            "UPDATE notices SET title = REPLACE(REPLACE(title, 'DUCKFRIEND', 'CODEFARMER'), 'codfarmer', 'CODEFARMER')"
        )


def list_notices() -> list[dict[str, Any]]:
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 10")]


def list_rankings() -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute("SELECT model_name, calls, tokens, updated_at FROM model_usage ORDER BY calls DESC LIMIT 20").fetchall()
    return [dict(row) for row in rows]


def create_user(email: str, password: str) -> bool:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    with connection() as db:
        try:
            cursor = db.execute("INSERT INTO users(email, password_hash) VALUES (?, ?)", (email.lower().strip(), f"{salt}${digest}"))
            db.execute("INSERT INTO wallets(user_id) VALUES (?)", (cursor.lastrowid,))
        except sqlite3.IntegrityError:
            return False
    return True


def verify_user(email: str, password: str) -> bool:
    with connection() as db:
        row = db.execute("SELECT password_hash FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    if not row:
        return False
    salt, digest = row["password_hash"].split("$", 1)
    return secrets.compare_digest(digest, hashlib.sha256(f"{salt}:{password}".encode()).hexdigest())


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    with connection() as db:
        row = db.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    if not row:
        return None
    salt, digest = row["password_hash"].split("$", 1)
    if not secrets.compare_digest(digest, hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()):
        return None
    return {"id": row["id"], "email": row["email"]}


def create_session(user_id: int, token: str, expires_at: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connection() as db:
        db.execute("DELETE FROM sessions WHERE expires_at <= CURRENT_TIMESTAMP")
        db.execute("INSERT INTO sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)", (token_hash, user_id, expires_at))


def get_session_user(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connection() as db:
        row = db.execute("""SELECT users.id, users.email FROM sessions JOIN users ON users.id = sessions.user_id
                           WHERE sessions.token_hash = ? AND sessions.expires_at > CURRENT_TIMESTAMP""", (token_hash,)).fetchone()
    return dict(row) if row else None


def delete_session(token: str | None) -> None:
    if token:
        with connection() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (hashlib.sha256(token.encode()).hexdigest(),))


def ensure_wallet(user_id: int) -> dict[str, Any]:
    with connection() as db:
        db.execute("INSERT OR IGNORE INTO wallets(user_id) VALUES (?)", (user_id,))
        row = db.execute("SELECT user_id, balance, currency, updated_at FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row)


def list_api_keys(user_id: int) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute("SELECT id, name, key_prefix, last_used_at, expires_at, revoked, created_at FROM api_keys WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    return [dict(row) for row in rows]


def create_api_key(user_id: int, name: str, expires_at: str | None = None) -> tuple[dict[str, Any], str]:
    raw = "cf-" + secrets.token_urlsafe(30)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:12]
    with connection() as db:
        row = db.execute("INSERT INTO api_keys(user_id, name, key_hash, key_prefix, expires_at) VALUES (?, ?, ?, ?, ?) RETURNING id, name, key_prefix, expires_at, revoked, created_at", (user_id, name.strip() or "默认密钥", key_hash, prefix, expires_at)).fetchone()
    return dict(row), raw


def revoke_api_key(user_id: int, key_id: int) -> bool:
    with connection() as db:
        result = db.execute("UPDATE api_keys SET revoked = 1 WHERE id = ? AND user_id = ?", (key_id, user_id))
    return result.rowcount > 0


def delete_api_key(user_id: int, key_id: int) -> bool:
    with connection() as db:
        result = db.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
    return result.rowcount > 0


def list_transactions(user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute("SELECT id, type, amount, balance_after, description, reference, created_at FROM wallet_transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, max(1, min(limit, 500)))).fetchall()
    return [dict(row) for row in rows]


def credit_wallet(user_id: int, amount: float, description: str, transaction_type: str = "credit", reference: str | None = None) -> dict[str, Any]:
    with connection() as db:
        db.execute("INSERT OR IGNORE INTO wallets(user_id) VALUES (?)", (user_id,))
        wallet = db.execute("SELECT balance FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
        balance = float(wallet["balance"]) + amount
        db.execute("UPDATE wallets SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (balance, user_id))
        row = db.execute("INSERT INTO wallet_transactions(user_id, type, amount, balance_after, description, reference) VALUES (?, ?, ?, ?, ?, ?) RETURNING id, type, amount, balance_after, description, reference, created_at", (user_id, transaction_type, amount, balance, description, reference)).fetchone()
    return dict(row)


def list_usage_logs(user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute("SELECT id, api_key_id, model_name, endpoint, prompt_tokens, completion_tokens, total_tokens, cost, status, latency_ms, created_at FROM usage_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, max(1, min(limit, 500)))).fetchall()
    return [dict(row) for row in rows]


def add_usage_log(user_id: int, values: dict[str, Any]) -> dict[str, Any]:
    prompt = int(values.get("prompt_tokens") or 0)
    completion = int(values.get("completion_tokens") or 0)
    total = int(values.get("total_tokens") if values.get("total_tokens") is not None else prompt + completion)
    with connection() as db:
        row = db.execute("INSERT INTO usage_logs(user_id, api_key_id, model_name, endpoint, prompt_tokens, completion_tokens, total_tokens, cost, status, latency_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING *", (user_id, values.get("api_key_id"), values["model_name"], values.get("endpoint", "chat.completions"), prompt, completion, total, float(values.get("cost", 0)), values.get("status", "success"), int(values.get("latency_ms", 0)))).fetchone()
    return dict(row)


def list_channels(user_id: int) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute("SELECT id, name, base_url, model_mapping, group_name, weight, enabled, created_at, updated_at FROM channels WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    return [dict(row) for row in rows]


def create_channel(user_id: int, values: dict[str, Any]) -> dict[str, Any]:
    import json
    with connection() as db:
        row = db.execute("INSERT INTO channels(user_id, name, base_url, api_key, model_mapping, group_name, weight, enabled) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id, name, base_url, model_mapping, group_name, weight, enabled, created_at, updated_at", (user_id, values["name"], values["base_url"], values.get("api_key", ""), json.dumps(values.get("model_mapping", {}), ensure_ascii=False), values.get("group_name", "default"), float(values.get("weight", 1)), int(bool(values.get("enabled", True))))).fetchone()
    result = dict(row); result["model_mapping"] = json.loads(result["model_mapping"]); return result


def update_channel(user_id: int, channel_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
    import json
    allowed = {"name", "base_url", "api_key", "model_mapping", "group_name", "weight", "enabled"}; changes = {k: v for k, v in values.items() if k in allowed}
    if not changes: return None
    if "model_mapping" in changes: changes["model_mapping"] = json.dumps(changes["model_mapping"], ensure_ascii=False)
    changes["enabled"] = int(bool(changes["enabled"])) if "enabled" in changes else None
    assignments = ", ".join(f"{k} = ?" for k in changes if changes[k] is not None) + ", updated_at = CURRENT_TIMESTAMP"
    params = [v for v in changes.values() if v is not None] + [channel_id, user_id]
    with connection() as db:
        row = db.execute(f"UPDATE channels SET {assignments} WHERE id = ? AND user_id = ? RETURNING id, name, base_url, model_mapping, group_name, weight, enabled, created_at, updated_at", params).fetchone()
    if not row: return None
    result = dict(row); result["model_mapping"] = json.loads(result["model_mapping"]); return result


def delete_channel(user_id: int, channel_id: int) -> bool:
    with connection() as db:
        result = db.execute("DELETE FROM channels WHERE id = ? AND user_id = ?", (channel_id, user_id))
    return result.rowcount > 0


def list_routes(user_id: int) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute("SELECT r.id, r.model_name, r.channel_id, c.name AS channel_name, r.priority, r.weight, r.enabled, r.created_at FROM model_routes r JOIN channels c ON c.id = r.channel_id WHERE r.user_id = ? ORDER BY r.priority DESC, r.id DESC", (user_id,)).fetchall()
    return [dict(row) for row in rows]


def resolve_route_channel(user_id: int, model_name: str) -> dict[str, Any] | None:
    """Return the highest-priority enabled channel for a model."""
    with connection() as db:
        row = db.execute(
            """SELECT c.id, c.name, c.base_url, c.api_key, c.model_mapping,
                      r.model_name, r.weight
                 FROM model_routes r
                 JOIN channels c ON c.id = r.channel_id
                WHERE r.user_id = ? AND r.model_name = ?
                  AND r.enabled = 1 AND c.enabled = 1
                ORDER BY r.priority DESC, r.weight DESC, r.id ASC
                LIMIT 1""",
            (user_id, model_name),
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    try:
        result["model_mapping"] = json.loads(result.get("model_mapping") or "{}")
    except (TypeError, ValueError):
        result["model_mapping"] = {}
    return result


def create_route(user_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
    with connection() as db:
        valid = db.execute("SELECT id FROM channels WHERE id = ? AND user_id = ?", (values["channel_id"], user_id)).fetchone()
        if not valid: return None
        row = db.execute("INSERT INTO model_routes(user_id, model_name, channel_id, priority, weight, enabled) VALUES (?, ?, ?, ?, ?, ?) RETURNING id, model_name, channel_id, priority, weight, enabled, created_at", (user_id, values["model_name"], values["channel_id"], int(values.get("priority", 0)), float(values.get("weight", 1)), int(bool(values.get("enabled", True))))).fetchone()
    return dict(row)


def delete_route(user_id: int, route_id: int) -> bool:
    with connection() as db:
        result = db.execute("DELETE FROM model_routes WHERE id = ? AND user_id = ?", (route_id, user_id))
    return result.rowcount > 0

