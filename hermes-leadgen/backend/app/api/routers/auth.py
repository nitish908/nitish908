from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AUTH_COOKIE_NAME, get_current_user
from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.csrf import CSRF_COOKIE_NAME, generate_csrf_token
from app.core.db import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(subject=str(user.id), role=user.role)
    response.set_cookie(
        AUTH_COOKIE_NAME, token, httponly=True, secure=settings.cookie_secure, samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        CSRF_COOKIE_NAME, generate_csrf_token(), httponly=False, secure=settings.cookie_secure, samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    record_audit(db, actor_id=user.id, action="login", object_type="user", object_id=str(user.id))
    db.commit()
    return user


@router.post("/logout")
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.delete_cookie(AUTH_COOKIE_NAME)
    response.delete_cookie(CSRF_COOKIE_NAME)
    record_audit(db, actor_id=user.id, action="logout", object_type="user", object_id=str(user.id))
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
