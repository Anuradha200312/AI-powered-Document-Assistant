"""
backend/middleware/auth_middleware.py
FastAPI dependency for JWT-protected routes.
"""
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User
from backend.services.auth_service import decode_access_token

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extracts and validates the Bearer JWT token,
    then loads and returns the authenticated User from the database.
    Raises HTTP 401 if the token is missing, invalid, expired, or the
    user no longer exists.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError as exc:
        logger.warning("Auth failed: %s", exc)
        raise credentials_exception from exc

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("Auth: user %s not found in DB.", user_id)
        raise credentials_exception

    return user
