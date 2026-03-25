"""OAuth2 authentication endpoints for Google sign-in."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.connectors.google_ads import (
    exchange_code_for_tokens,
    get_oauth_authorize_url,
    get_user_info,
    refresh_access_token,
)
from app.models.database import User, get_db
from app.models.schemas import OAuthCallbackResponse, OAuthLoginResponse, TokenRefreshResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_jwt(user_id: str, email: str) -> str:
    """Create a signed JWT for the given user."""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    token: str = Query(None, alias="token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract the current user from the Authorization header or query param."""
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    # Strip "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/login", response_model=OAuthLoginResponse)
async def login():
    """Return the Google OAuth2 authorization URL."""
    state = secrets.token_urlsafe(32)
    url = get_oauth_authorize_url(state)
    return OAuthLoginResponse(authorization_url=url)


@router.get("/callback", response_model=OAuthCallbackResponse)
async def callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Exchange the OAuth2 authorization code for tokens, create/update user."""
    # Exchange code for tokens
    token_data = await exchange_code_for_tokens(code)
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")

    # Get user info from Google
    user_info = await get_user_info(access_token)
    email = user_info.get("email", "")
    name = user_info.get("name", "")

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from Google")

    # Find or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        user.google_access_token_encrypted = access_token
        if refresh_token:
            user.google_refresh_token_encrypted = refresh_token
        user.name = name
        user.google_token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )
    else:
        user = User(
            id=uuid4(),
            email=email,
            name=name,
            google_access_token_encrypted=access_token,
            google_refresh_token_encrypted=refresh_token,
            google_token_expires_at=datetime.now(timezone.utc) + timedelta(
                seconds=token_data.get("expires_in", 3600)
            ),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    # Create JWT
    app_token = create_jwt(str(user.id), email)

    return OAuthCallbackResponse(
        access_token=app_token,
        token_type="bearer",
        user_id=str(user.id),
        email=email,
    )


@router.get("/refresh", response_model=TokenRefreshResponse)
async def refresh(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh the Google OAuth access token and return a new JWT."""
    if not user.google_refresh_token_encrypted:
        raise HTTPException(status_code=400, detail="No refresh token stored for user")

    token_data = await refresh_access_token(user.google_refresh_token_encrypted)
    user.google_access_token_encrypted = token_data["access_token"]
    user.google_token_expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=token_data.get("expires_in", 3600)
    )
    await db.commit()

    new_jwt = create_jwt(str(user.id), user.email)
    return TokenRefreshResponse(access_token=new_jwt)
