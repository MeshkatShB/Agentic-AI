"""Authentication API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional
from datetime import timedelta
from pydantic import BaseModel, EmailStr

from backend.config import settings
from backend.models import get_db, User
from backend.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_admin_user,
    get_password_hash
)

router = APIRouter()
logger = logging.getLogger(__name__)


class UserSignup(BaseModel):
    """User signup request."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login response."""
    access_token: str
    token_type: str
    user: dict


class UserProfile(BaseModel):
    """User profile response."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_superuser: bool = False
    preferences: Optional[dict] = {}
    allowed_tools: list = []
    created_at: str


@router.post("/signup", response_model=UserProfile)
async def signup(
    user_data: UserSignup,
    db: Session = Depends(get_db)
):
    """Create a new user account."""
    
    # Check if username exists
    existing_user = db.query(User).filter(
        User.username == user_data.username
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    existing_email = db.query(User).filter(
        User.email == user_data.email
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserProfile(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_superuser=getattr(new_user, "is_superuser", False),
        preferences=new_user.preferences,
        allowed_tools=new_user.allowed_tools,
        created_at=new_user.created_at.isoformat()
    )


@router.post("/login", response_model=UserLogin)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with username and password."""
    
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return UserLogin(
        access_token=access_token,
        token_type="bearer",
        user=user.to_dict()
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout the current user."""
    
    # In a real implementation, you might want to:
    # - Invalidate the token (store in a blacklist)
    # - Clear any server-side session data
    # - Clear agent state
    
    from backend.agent import agent_executor
    agent_executor.clear_agent(current_user.id)
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    
    logger.info(f"GET /auth/me for user {current_user.username}")
    logger.info(f"User allowed_tools: {current_user.allowed_tools}")
    
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_superuser=getattr(current_user, "is_superuser", False),
        preferences=current_user.preferences or {},
        allowed_tools=current_user.allowed_tools or [],
        created_at=current_user.created_at.isoformat()
    )


@router.put("/me", response_model=UserProfile)
async def update_profile(
    updates: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    
    logger.info(f"Updating profile for user {current_user.username}: {updates}")
    
    # Update allowed fields
    allowed_fields = ["full_name", "email", "preferences", "allowed_tools"]
    
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(current_user, field, value)
            # Mark JSON fields as modified so SQLAlchemy knows to update them
            if field in ["preferences", "allowed_tools"]:
                flag_modified(current_user, field)
    
    db.commit()
    db.refresh(current_user)
    
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_superuser=getattr(current_user, "is_superuser", False),
        preferences=current_user.preferences,
        allowed_tools=current_user.allowed_tools,
        created_at=current_user.created_at.isoformat()
    )


class ChangePasswordBody(BaseModel):
    """Change password request body."""
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    body: ChangePasswordBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    
    # Verify old password
    from backend.auth import verify_password
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


# --- Admin user management (JWT-protected, admin-only) ---

class UserListItem(BaseModel):
    """User summary for admin list."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: str


class AdminUserCreate(BaseModel):
    """Admin create user request."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    is_superuser: bool = False


@router.get("/users", response_model=List[UserListItem])
async def list_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        UserListItem(
            id=u.id,
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            is_superuser=getattr(u, "is_superuser", False),
            created_at=u.created_at.isoformat() if u.created_at else ""
        )
        for u in users
    ]


@router.post("/users", response_model=UserListItem)
async def admin_create_user(
    data: AdminUserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)."""
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    hashed = get_password_hash(data.password)
    new_user = User(
        username=data.username,
        email=data.email,
        hashed_password=hashed,
        full_name=data.full_name,
        is_superuser=data.is_superuser
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserListItem(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        is_superuser=getattr(new_user, "is_superuser", False),
        created_at=new_user.created_at.isoformat() if new_user.created_at else ""
    )


@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only). Cannot delete self."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
