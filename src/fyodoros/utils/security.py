import os
from pathlib import Path
from cryptography.fernet import Fernet

ENC_PREFIX = "ENC:"

def _get_key_path():
    """Returns the path to the encryption key."""
    fyodor_dir = Path.home() / ".fyodor"
    fyodor_dir.mkdir(parents=True, exist_ok=True)
    return fyodor_dir / "secret.key"

def get_key():
    """
    Retrieves the existing encryption key or generates a new one.
    """
    key_path = _get_key_path()
    if key_path.exists():
        with open(key_path, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        # Create file with strict permissions
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key)
        return key

def encrypt_value(value: str) -> str:
    """
    Encrypts a string value.
    Returns the value prefixed with ENC: to identify it as encrypted.
    """
    if not value:
        return ""
    key = get_key()
    f = Fernet(key)
    encrypted = f.encrypt(value.encode()).decode()
    return f"{ENC_PREFIX}{encrypted}"

def decrypt_value(value: str) -> str:
    """
    Decrypts a string value if it is encrypted (starts with ENC:).
    Otherwise returns the original value.
    """
    if not value.startswith(ENC_PREFIX):
        return value

    clean_value = value[len(ENC_PREFIX):]
    key = get_key()
    f = Fernet(key)
    try:
        decrypted = f.decrypt(clean_value.encode()).decode()
        return decrypted
    except Exception:
        # If decryption fails, return original (or empty? Safe to return original if it was just garbage)
        return value
