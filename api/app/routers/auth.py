from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.limiter import limiter
from app.models.user import User
from app.auth.security import verify_password, create_access_token
from app.audit import log_auth_event

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
