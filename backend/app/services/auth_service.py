from sqlalchemy.orm import Session
from datetime import datetime
from typing import Tuple, Optional

from app.models.user import User
from app.utils.jwt_helper import generate_access_token, generate_refresh_token

class AuthService:
    @staticmethod
    def register_user(db: Session, email: str, password: str, full_name: str, role: str = 'AppUser') -> Tuple[Optional[User], Optional[str]]:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return None, "Email already exists"
            
        try:
            user = User(
                email=email,
                full_name=full_name,
                role=role
            )
            user.set_password(password)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user, None
        except Exception as e:
            db.rollback()
            return None, str(e)

    @staticmethod
    def login_user(db: Session, email: str, password: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.check_password(password):
            return None, None, "Invalid email or password"
            
        if not user.is_active:
            return None, None, "Account is inactive"
            
        try:
            user.last_login = datetime.utcnow()
            db.commit()
            
            # Generate tokens
            access_token = generate_access_token(user.id, user.role)
            refresh_token = generate_refresh_token(user.id)
            
            return access_token, refresh_token, None
        except Exception as e:
            db.rollback()
            return None, None, str(e)
            
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
