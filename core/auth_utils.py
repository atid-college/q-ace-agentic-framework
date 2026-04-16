import hashlib
import time
from typing import Optional, Dict, Any
import json
import base64
import os

# Secret for JWT-like token (In production, use a secure env variable)
SECRET_KEY = os.environ.get("Q_ACE_SECRET_KEY", "q-ace-secret-super-key-2026")

# Session timeout in seconds (default: 3600 = 1 hour). Override via Q_ACE_SESSION_TIMEOUT in .env
SESSION_TIMEOUT = int(os.environ.get("Q_ACE_SESSION_TIMEOUT", 3600))

def hash_password(password: str) -> str:
    """Hashes a password using SHA256 (Simple version for scaffold)."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a password against its SHA256 hash."""
    return hash_password(password) == password_hash

def create_access_token(data: dict, expires_in: Optional[int] = None) -> str:
    """Creates a simple base64 encoded token with expiration."""
    if expires_in is None:
        expires_in = SESSION_TIMEOUT
    payload = data.copy()
    payload["exp"] = time.time() + expires_in
    
    payload_json = json.dumps(payload)
    payload_b64 = base64.b64encode(payload_json.encode()).decode()
    
    # Simple signature (HMAC-like)
    sig = hashlib.sha256(f"{payload_b64}{SECRET_KEY}".encode()).hexdigest()
    
    return f"{payload_b64}.{sig}"

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies the simple base64 token."""
    try:
        if "." not in token:
            return None

        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, sig = parts

        # Verify signature
        expected_sig = hashlib.sha256(f"{payload_b64}{SECRET_KEY}".encode()).hexdigest()
        if sig != expected_sig:
            return None

        payload_json = base64.b64decode(payload_b64).decode()
        payload = json.loads(payload_json)

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None



