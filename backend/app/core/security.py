from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security_bearer = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Computes a secure bcrypt hash for password storage."""
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

def create_access_token(subject: str, role: str = "viewer", expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token with user_id and RBAC role."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "role": str(role)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> str:
    """FastAPI dependency to extract user_id from Bearer token. Defaults to 'guest' if unauthenticated."""
    if not credentials:
        return "guest_user"
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload["sub"]

async def get_current_user_role(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> str:
    """FastAPI dependency to extract user role from Bearer token. Defaults to 'viewer' if unauthenticated."""
    if not credentials:
        return "viewer"
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        return "viewer"
    return payload.get("role", "viewer")
