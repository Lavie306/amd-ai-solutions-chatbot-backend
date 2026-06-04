"""
JWT Auth — Login + token verification.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import bcrypt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.schemas.schemas import LoginRequest, TokenOut

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["Auth"])

bearer = HTTPBearer()

# Hard-code admin duy nhất (đủ cho scope intern)
ADMIN_EMAIL = settings.admin_email
ADMIN_PASSWORD_HASH = bcrypt.hashpw(settings.admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest) -> TokenOut:
    if body.email != ADMIN_EMAIL or not bcrypt.checkpw(body.password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng",
        )
    token = create_access_token(subject=body.email)
    return TokenOut(access_token=token)


# ─────────────────────────────────────────────
# Dependency để protect endpoints
# ─────────────────────────────────────────────
async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    """FastAPI dependency — yêu cầu JWT hợp lệ."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("sub", "")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
