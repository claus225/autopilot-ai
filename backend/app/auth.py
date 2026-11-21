"""Small security primitives for the future private owner account.

These helpers do not create accounts, authenticate HTTP requests, or issue cookies.
They are intentionally isolated until the complete session and CSRF flow is tested.
"""
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a password with Argon2id; never store the raw password."""
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Le mot de passe doit contenir au moins 12 caractères.")
    if len(password) > 1024:
        raise ValueError("Le mot de passe est trop long.")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without revealing why a stored hash is invalid."""
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError, TypeError):
        return False


def create_secret_token() -> str:
    """Create a cryptographically random URL-safe token for a session or CSRF."""
    return secrets.token_urlsafe(32)


def fingerprint_token(token: str) -> str:
    """Return the SHA-256 fingerprint to store instead of a raw session token."""
    if not isinstance(token, str) or not token:
        raise ValueError("Jeton invalide.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(candidate: str, expected_fingerprint: str) -> bool:
    """Compare a presented token with its stored fingerprint in constant time."""
    if not isinstance(candidate, str) or not isinstance(expected_fingerprint, str):
        return False
    if len(expected_fingerprint) != 64:
        return False
    try:
        actual = fingerprint_token(candidate)
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected_fingerprint)
