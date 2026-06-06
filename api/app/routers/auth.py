from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.limiter import limiter
from app.models.user import User
from app.models.schemas import UserCreate, UserResponse
from app.auth.security import verify_password, create_access_token, get_password_hash
from app.auth.dependencies import get_current_user, require_admin, ROLE_HIERARCHY
from app.audit import log_auth_event, log_action

router = APIRouter(prefix="/auth", tags=["auth"])


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
    log_auth_event("auth_success", user.username, success=True, ip=ip)
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
    log_action("user_created", admin.username, target=payload.username, detail=f"role={payload.role}")
    return user
