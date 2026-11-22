import os
import json
import hashlib
import secrets
from pathlib import Path
from typing import Optional

STORAGE_DIR = os.getenv("STORAGE_DIR", "/data")
AUTH_FILE = Path(STORAGE_DIR) / "vault_auth.json"

def is_setup_completed() -> bool:
    return AUTH_FILE.exists()

def create_admin_user(username: str, password: str) -> dict:
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    session_secret = secrets.token_hex(32)
    data = {
        "username": username.strip(),
        "salt": salt,
        "password_hash": hashed,
        "session_secret": session_secret
    }
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data

def verify_credentials(username: str, password: str) -> bool:
    if not is_setup_completed():
        return False
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("username") != username.strip():
            return False
        salt = data.get("salt")
        expected_hash = data.get("password_hash")
        current_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return secrets.compare_digest(expected_hash, current_hash)
    except Exception:
        return False

def get_session_secret() -> str:
    if not is_setup_completed():
        return "default_uninitialized_secret"
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("session_secret", "fallback_secret")
    except Exception:
        return "fallback_secret"
