from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.limiter import limiter
from app.models.user import User
from app.models.schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
    PasswordReset,
    PasswordChange,
)
from app.auth.security import verify_password, create_access_token, get_password_hash
from app.auth.dependencies import get_current_user, require_admin, ROLE_HIERARCHY
from app.audit import log_auth_event, log_action

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _active_admin_count(db: Session, exclude_id: int | None = None) -> int:
    """Count active admins, optionally excluding one user — used to prevent
    demoting or deactivating the last administrator (self-lockout guard)."""
    q = db.query(User).filter(User.role == "admin", User.is_active.is_(True))
    if exclude_id is not None:
        q = q.filter(User.id != exclude_id)
    return q.count()


@router.post("/token")
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    ip = request.client.host if request.client else ""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        log_auth_event("auth_failure", form_data.username, success=False, ip=ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        log_auth_event("auth_failure_inactive", user.username, success=False, ip=ip, role=user.role)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    log_auth_event("auth_success", user.username, success=True, ip=ip, role=user.role)
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_current_user(user: User = Depends(get_current_user)):
    """Return the authenticated user's identity and role (used by the UI)."""
    return user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_user(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Provision a new user with a role. Admin-only."""
    if payload.role not in ROLE_HIERARCHY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(ROLE_HIERARCHY)}",
        )
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action("user_created", admin.username, target=payload.username,
               detail=f"role={payload.role}", ip=_client_ip(request))
    return user


@router.get("/users", response_model=List[UserResponse])
async def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """List all users with their roles and status. Admin-only."""
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update a user's role and/or active status. Admin-only.

    Guards against removing the last active administrator (self-lockout).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.role is not None and payload.role not in ROLE_HIERARCHY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(ROLE_HIERARCHY)}",
        )

    # Last-admin protection: block a change that would leave zero active admins.
    demoting = payload.role is not None and payload.role != "admin" and user.role == "admin"
    deactivating = payload.is_active is False and user.is_active and user.role == "admin"
    if (demoting or deactivating) and _active_admin_count(db, exclude_id=user.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last active administrator",
        )

    changes = []
    if payload.role is not None and payload.role != user.role:
        user.role = payload.role
        changes.append(f"role={payload.role}")
    if payload.is_active is not None and payload.is_active != user.is_active:
        user.is_active = payload.is_active
        changes.append(f"is_active={payload.is_active}")

    if changes:
        db.commit()
        db.refresh(user)
        log_action("user_updated", admin.username, target=user.username,
                   detail=",".join(changes), ip=_client_ip(request))
    return user


@router.post("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    user_id: int,
    payload: PasswordReset,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin reset of another user's password. Admin-only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    log_action("user_password_reset", admin.username, target=user.username, ip=_client_ip(request))


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    payload: PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Authenticated user changes their own password (verifies current one)."""
    if not verify_password(payload.current_password, user.hashed_password):
        log_auth_event("password_change_failed", user.username, success=False,
                       ip=_client_ip(request), role=user.role)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    log_action("user_password_changed", user.username, target=user.username, ip=_client_ip(request))
