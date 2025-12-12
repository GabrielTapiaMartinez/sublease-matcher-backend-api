from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select

from ..adapters.sqlalchemy import models
from ..dependencies.uow import get_uow
from ..interfaces.uow import UnitOfWork

security = HTTPBearer()

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    uow: UnitOfWork = Depends(get_uow)
) -> models.User:
    token = creds.credentials
    
    # Check session
    stmt = select(models.Session).where(models.Session.id == token)
    session = uow.session.scalars(stmt).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Check expiry if applicable
    # if session.expires_at and session.expires_at < now(): ...
    
    return session.user

def get_current_user_id(
    user: models.User = Depends(get_current_user)
) -> str:
    return user.id
