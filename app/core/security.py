# app/core/security.py — JWT auth, RBAC, password hashing
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

# Password hashing — O(1) per hash
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt. O(1)
    
    Note: bcrypt has a 72-byte limit on passwords, so we truncate if necessary.
    """
    # Truncate password to 72 bytes (bcrypt limit) if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash. O(1)"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token. O(1)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT token. O(1)"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """Extract and validate user from JWT token. O(1)"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return payload


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[dict]:
    """Optionally extract user - returns None if no token. O(1)"""
    if credentials is None:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except HTTPException:
        return None


def require_role(allowed_roles: List[str]):
    """RBAC dependency factory — checks user role against allowed roles. O(r) where r = number of roles"""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "analyst")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' not authorized. Required: {allowed_roles}",
            )
        return current_user
    return role_checker


# Simple in-memory rate limiter
class RateLimiter:
    """Simple sliding-window rate limiter. O(1) amortized"""
    def __init__(self):
        self._requests: dict[str, list[float]] = {}

    def check(self, key: str, limit: int = settings.RATE_LIMIT_PER_MINUTE, window: int = 60) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        if key not in self._requests:
            self._requests[key] = []

        # Remove expired entries
        self._requests[key] = [
            t for t in self._requests[key] if now - t < window
        ]

        if len(self._requests[key]) >= limit:
            return False

        self._requests[key].append(now)
        return True


rate_limiter = RateLimiter()
