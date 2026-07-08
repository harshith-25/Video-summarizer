from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.utils.jwt_helper import decode_token
from app.models.user import User

logger = logging.getLogger("app")

# APIKeyHeader will search for the "Authorization" header
authorization_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_current_user(auth_header: str = Depends(authorization_header), db: Session = Depends(get_db)) -> User:
    if not auth_header:
        logger.warning('No token provided')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing"
        )
    
    token = auth_header
    # Standard format: "Bearer <token>"
    if auth_header.startswith("Bearer "):
        parts = auth_header.split(" ")
        if len(parts) == 2:
            token = parts[1]
        else:
            logger.warning('Invalid Authorization header format')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
            
    payload = decode_token(token)
    if not payload:
        logger.warning('Invalid or expired token')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
        
    if payload.get('type') != 'access':
        logger.warning('Invalid token type')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
        
    user = db.query(User).filter(User.id == payload.get('user_id')).first()
    if not user or not user.is_active:
        logger.warning(f'User not found or inactive: {payload.get("user_id")}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
        
    logger.info(f'User authenticated: {user.email} (ID: {user.id}, Role: {user.role})')
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != 'Admin':
        logger.warning(f'Admin access denied for user: {current_user.email}')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    logger.info(f'Admin access granted: {current_user.email}')
    return current_user
