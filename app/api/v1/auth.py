# app/api/v1/auth.py — Authentication endpoints
"""
Auth Router: Login, register, and user management.
Supports both direct email/password and Firebase token validation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import User
from app.core.security import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_optional_user
)
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse,
    UserResponse, FirebaseTokenLogin, UserUpdate
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user with email/password and return JWT token.
    O(1) — single DB lookup by indexed email
    """
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.
    O(1) — single DB insert
    """
    # Check if email exists
    existing = await db.execute(
        select(User).where(User.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=request.email,
        name=request.name,
        hashed_password=hash_password(request.password),
        role=request.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/firebase-login", response_model=TokenResponse)
async def firebase_login(request: FirebaseTokenLogin, db: AsyncSession = Depends(get_db)):
    """
    Validate Firebase token and issue backend JWT.
    For now, accepts the token and creates/gets a user record.
    In production: verify with Firebase Admin SDK.
    O(1)
    """
    # In production, you'd verify the Firebase token here:
    # decoded = firebase_admin.auth.verify_id_token(request.firebase_token)
    # For now, we'll create a user based on the token claim simulation

    # Try to find existing user by firebase_uid (using token as placeholder)
    # In real implementation, decode the token first
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Firebase token login requires Firebase Admin SDK. Use email/password login instead.",
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user profile. O(1)"""
    result = await db.execute(
        select(User).where(User.id == current_user["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    update: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile. O(1)"""
    result = await db.execute(
        select(User).where(User.id == current_user["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update.name is not None:
        user.name = update.name
    if update.avatar_url is not None:
        user.avatar_url = update.avatar_url

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)
