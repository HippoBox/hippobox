import hashlib
import secrets

from passlib.context import CryptContext
from passlib.exc import UnknownHashError

# ---------------------------------------------------------
# Password Security (Argon2 / Bcrypt)
# ---------------------------------------------------------
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    Used for User Login.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (UnknownHashError, ValueError):
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using Argon2 or Bcrypt.
    Used during User Signup / Password Reset.
    """
    return pwd_context.hash(password)


# ---------------------------------------------------------
# API Key Security (SHA256)
# ---------------------------------------------------------
def generate_api_key() -> str:
    """
    Generate a random API Key starting with 'sk-'.
    Example output: sk-Law8... (48 chars total)
    """
    # 35 bytes of randomness -> urlsafe base64 string
    return f"sk-{secrets.token_urlsafe(35)}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()
