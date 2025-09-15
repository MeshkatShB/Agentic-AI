"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta
from pydantic import BaseModel, EmailStr

from backend.config import settings
from backend.models import get_db, User
from backend.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash
)

router = APIRouter()


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
    preferences: dict
    allowed_tools: list
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
    
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        preferences=current_user.preferences,
        allowed_tools=current_user.allowed_tools,
        created_at=current_user.created_at.isoformat()
    )


@router.put("/me", response_model=UserProfile)
async def update_profile(
    updates: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    
    # Update allowed fields
    allowed_fields = ["full_name", "email", "preferences", "allowed_tools"]
    
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        preferences=current_user.preferences,
        allowed_tools=current_user.allowed_tools,
        created_at=current_user.created_at.isoformat()
    )


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    
    # Verify old password
    from backend.auth import verify_password
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
