from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.db.database import get_db
from app.models.user import User
from app.audit import log_auth_event

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            log_auth_event("token_rejected", "", success=False)
            raise credentials_exception
    except JWTError:
        log_auth_event("token_rejected", "", success=False)
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        log_auth_event("token_rejected", username, success=False)
        raise credentials_exception

    request.state.username = user.username
    return user
