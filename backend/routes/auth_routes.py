from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

import models
import schemas
from database import get_db
from services.auth import verify_password, create_access_token, get_current_user

logger = logging.getLogger("HospitalAI-Auth-Routes")

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
        samesite="none",
        secure=True
    )
    
    user.token = access_token
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

@router.get("/sso/login")
async def sso_login(request: Request):
    """Initiate OAuth2/OIDC SSO authorization redirect."""
    import os
    from fastapi.responses import RedirectResponse
    
    sso_mock = os.getenv("SSO_MOCK", "false").lower() == "true"
    client_id = os.getenv("SSO_CLIENT_ID")
    auth_url = os.getenv("SSO_AUTHORIZATION_URL")
    redirect_uri = os.getenv("SSO_REDIRECT_URI", "http://localhost:8000/api/auth/sso/callback")
    
    # Bypasses external provider redirects if mock mode is active
    if sso_mock or not client_id or not auth_url:
        logger.info("SSO Mock/Fallback enabled. Redirecting directly to local callback.")
        return RedirectResponse(url=f"/api/auth/sso/callback?code=mock_sso_code&state=mock_state")
        
    sso_redirect_url = f"{auth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=openid+profile+email&state=sso_state_123"
    return RedirectResponse(url=sso_redirect_url)

@router.get("/sso/callback")
async def sso_callback(
    code: str,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Callback to exchange SSO code, map clinical_staff claims, and provision user sessions."""
    import os
    import uuid
    import requests
    from fastapi.responses import RedirectResponse
    from services.auth import hash_password
    
    sso_mock = os.getenv("SSO_MOCK", "false").lower() == "true" or code == "mock_sso_code"
    client_id = os.getenv("SSO_CLIENT_ID")
    client_secret = os.getenv("SSO_CLIENT_SECRET")
    token_url = os.getenv("SSO_TOKEN_URL")
    userinfo_url = os.getenv("SSO_USERINFO_URL")
    redirect_uri = os.getenv("SSO_REDIRECT_URI", "http://localhost:8000/api/auth/sso/callback")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    email = None
    username = None
    groups = []
    
    if sso_mock or not client_id or not token_url or not userinfo_url:
        # Standard simulated AD claims for development testing
        email = "sso_clinician@hospitalai.com"
        username = "sso_clinician"
        groups = ["clinical_staff"]
    else:
        try:
            token_res = requests.post(token_url, data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret
            }, timeout=10.0)
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            
            userinfo_res = requests.get(userinfo_url, headers={
                "Authorization": f"Bearer {access_token}"
            }, timeout=10.0)
            userinfo = userinfo_res.json()
            
            email = userinfo.get("email")
            username = userinfo.get("preferred_username") or email.split("@")[0]
            groups = userinfo.get("groups", [])
            # Support alternate claim naming
            if not groups and "roles" in userinfo:
                groups = userinfo.get("roles", [])
        except Exception as e:
            logger.error(f"Failed to communicate with SSO identity provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="SSO authentication handshake failed."
            )
            
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO provider did not return user email."
        )
        
    # Map groups to internal DB roles
    role = models.UserRole.DOCTOR
    groups_lower = [g.lower() for g in groups]
    if "admin" in groups_lower:
        role = models.UserRole.ADMIN
    elif "coordinator" in groups_lower:
        role = models.UserRole.COORDINATOR
    elif "clinical_staff" in groups_lower or "nurse" in groups_lower or "doctor" in groups_lower:
        role = models.UserRole.DOCTOR
        
    # Check if user exists
    user_res = await db.execute(
        select(models.User).where(models.User.email == email)
    )
    user = user_res.scalar_one_or_none()
    
    if not user:
        logger.info(f"Auto-provisioning user {username} ({email}) with role {role}")
        user = models.User(
            username=username,
            email=email,
            hashed_password=hash_password(str(uuid.uuid4())),
            role=role,
            is_active=True
        )
        db.add(user)
        await db.flush()
    else:
        # Sync role updates
        if user.role != role:
            user.role = role
            db.add(user)
            await db.flush()
            
    internal_token = create_access_token(data={"sub": user.username})
    
    is_prod = os.getenv("DATABASE_URL") is not None
    samesite_flag = "none" if is_prod else "lax"
    secure_flag = True if is_prod else False
    
    # Strip any trailing slash from frontend_url
    if frontend_url.endswith("/"):
        frontend_url = frontend_url[:-1]
        
    response = RedirectResponse(url=f"{frontend_url}/login?token={internal_token}")
    response.set_cookie(
        key="auth_token",
        value=internal_token,
        httponly=True,
        max_age=3600 * 24,
        expires=3600 * 24,
        samesite="none",
        secure=True
    )
    return response
