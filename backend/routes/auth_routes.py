from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import models
import schemas
from database import get_db
from services.auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=schemas.UserResponse)
async def login(
    payload: schemas.LoginPayload,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate credentials, generate a JWT token, and set it in a HttpOnly cookie."""
    # Find user by email
    res = await db.execute(
        select(models.User)
        .where(models.User.email == payload.email)
    )
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
        
    # Verify password
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account."
        )
        
    # Create JWT access token
    access_token = create_access_token(data={"sub": user.username})
    
    # Determine secure and samesite flags based on environment
    import os
    is_prod = os.getenv("DATABASE_URL") is not None
    samesite_flag = "none" if is_prod else "lax"
    secure_flag = True if is_prod else False
    
    # Set HttpOnly Cookie
    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        max_age=3600 * 24,  # 1 day expiration
        expires=3600 * 24,
        samesite=samesite_flag,
        secure=secure_flag
    )
    
    return user

@router.post("/logout")
async def logout(response: Response):
    """Clear the auth HttpOnly cookie."""
    import os
    is_prod = os.getenv("DATABASE_URL") is not None
    samesite_flag = "none" if is_prod else "lax"
    secure_flag = True if is_prod else False
    
    response.delete_cookie(
        key="auth_token",
        httponly=True,
        samesite=samesite_flag,
        secure=secure_flag
    )
    return {"message": "Successfully logged out."}

@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user: models.User = Depends(get_current_user)):
    """Retrieve details of the currently authenticated user."""
    return current_user
