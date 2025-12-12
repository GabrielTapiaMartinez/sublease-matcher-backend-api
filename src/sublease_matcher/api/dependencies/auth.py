from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..dependencies.uow import get_uow
from ..interfaces.repos import UserProtocol
from ..interfaces.uow import UnitOfWork

security = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security), uow: UnitOfWork = Depends(get_uow)
) -> UserProtocol:
    token = creds.credentials

    # Check session
    # Check session
    session = uow.sessions.get(token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiry if applicable
    # if session.expires_at and session.expires_at < now(): ...

    user = uow.users.get(session.user_id)
    if not user:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_id(user: UserProtocol = Depends(get_current_user)) -> str:
    return user.id
