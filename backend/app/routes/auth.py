from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.services.auth_service import AuthService
from app.middleware.auth_middleware import get_current_user, get_current_admin
from app.models.user import User
from app.config import Config

# Pydantic schemas for validation
from pydantic import BaseModel, EmailStr

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = 'AppUser'

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class ResetUserPasswordRequest(BaseModel):
    user_id: int
    new_password: str

class CreateAdminRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

logger = logging.getLogger("app")
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignUpRequest, db: Session = Depends(get_db)):
    if req.role not in ['AppUser', 'Admin']:
        role = 'AppUser'
    else:
        role = req.role
        
    user, error = AuthService.register_user(db, req.email, req.password, req.full_name, role)
    if error:
        logger.warning(f'Signup failed: {error}')
        raise HTTPException(status_code=400, detail=error)
        
    logger.info(f'New user registered: {user.email} (Role: {user.role})')
    return {
        'message': 'User registered successfully',
        'user': user.to_dict()
    }

@auth_router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    access_token, refresh_token, error = AuthService.login_user(db, req.email, req.password)
    if error:
        logger.warning(f'Login failed for {req.email}: {error}')
        raise HTTPException(status_code=401, detail=error)
        
    logger.info(f'User logged in: {req.email}')
    return {
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer'
    }

@auth_router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    logger.info(f'User profile accessed: {current_user.email}')
    return {'user': current_user.to_dict()}

@auth_router.get("/users")
def get_all_users(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    users = db.query(User).all()
    logger.info(f'Admin {current_admin.email} accessed user list')
    return {'users': [user.to_dict() for user in users]}

@auth_router.put("/users/{user_id}/toggle-status")
def toggle_user_status(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        
    user.is_active = not user.is_active
    db.commit()
    
    status_label = 'activated' if user.is_active else 'deactivated'
    logger.info(f'Admin {current_admin.email} {status_label} user {user.email}')
    return {
        'message': f'User {status_label} successfully',
        'user': user.to_dict()
    }

@auth_router.post("/change-password")
def change_password(req: ChangePasswordRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
        
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
    if not current_user.check_password(req.current_password):
        logger.warning(f'User {current_user.email} entered incorrect current password')
        raise HTTPException(status_code=422, detail="Current password is incorrect")
        
    current_user.set_password(req.new_password)
    db.commit()
    logger.info(f'User {current_user.email} changed password successfully')
    return {'message': 'Password changed successfully'}

@auth_router.post("/admin/reset-user-password")
def admin_reset_user_password(req: ResetUserPasswordRequest, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.set_password(req.new_password)
    db.commit()
    logger.info(f'Admin {current_admin.email} reset password for user {user.email}')
    return {'message': f'Password reset successfully for {user.email}'}

@auth_router.post("/admin/create-admin", status_code=status.HTTP_201_CREATED)
def create_admin(req: CreateAdminRequest, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
        
    user = User(email=req.email, full_name=req.full_name, role='Admin')
    user.set_password(req.password)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f'Admin {current_admin.email} created new admin: {user.email}')
    return {
        'message': 'Admin created successfully',
        'user': user.to_dict()
    }

@auth_router.get("/health")
def health_check():
    return {
        'status': 'ok',
        'message': 'Backend is running',
        'database': 'PostgreSQL'
    }
