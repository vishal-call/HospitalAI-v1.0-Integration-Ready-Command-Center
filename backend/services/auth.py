import os
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import models
from models import UserRole
from database import get_db

logger = logging.getLogger("HospitalAI-Auth")

# Security Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_hospital_ai_security_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3600  # Long duration for coordinate center sessions

def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a bcrypt hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token signature has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    FastAPI dependency injection to validate cookie-based JWT
    and retrieve the authenticated database user.
    """
    token = request.cookies.get("auth_token")
    if not token:
        # Fallback to Authorization Header for cross-domain/no-cookie clients
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )
        
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials."
        )
        
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject claim."
        )
        
    # Query database for user
    res = await db.execute(
        select(models.User)
        .where(models.User.username == username)
    )
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token does not exist."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deactivated."
        )
        
    return user

def check_roles(allowed_roles: List[UserRole]):
    """
    Dynamic dependency generator for endpoint role protection (RBAC).
    """
    async def role_checker(
        current_user: models.User = Depends(get_current_user)
    ) -> models.User:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"RBAC VIOLATION: User {current_user.username} (Role: {current_user.role}) "
                f"attempted unauthorized access to endpoint requiring {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Insufficient permissions for this action."
            )
        return current_user
    return role_checker


async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[models.User]:
    """
    FastAPI dependency injection to optionally validate JWT token.
    Returns user if authenticated, or None if unauthenticated.
    """
    token = request.cookies.get("auth_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            
    if not token:
        return None
        
    payload = decode_access_token(token)
    if not payload:
        return None
        
    username: str = payload.get("sub")
    if not username:
        return None
        
    res = await db.execute(
        select(models.User)
        .where(models.User.username == username)
    )
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        return None
        
    return user
