from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.db.database import get_db
from app.models.user import User
from app.audit import log_auth_event

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Role-based access control. Roles are hierarchical: a higher-ranked role
# implicitly satisfies every lower requirement (admin can do anything an
# operator can, an operator anything a viewer can).
ROLE_HIERARCHY = {"viewer": 1, "operator": 2, "admin": 3}


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


def require_role(minimum_role: str):
    """
    Dependency factory enforcing a *minimum* role (see ROLE_HIERARCHY).

    Returns the authenticated ``User`` so handlers can attribute actions to the
    caller. Denials are audit-logged. Usage:

        @router.delete("/cache")
        async def clear(user: User = Depends(require_admin)): ...
    """
    minimum_rank = ROLE_HIERARCHY[minimum_role]

    def checker(user: User = Depends(get_current_user)) -> User:
        if ROLE_HIERARCHY.get(user.role, 0) < minimum_rank:
            log_auth_event("authz_denied", user.username, success=False)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this operation",
            )
        return user

    return checker


# Pre-built dependencies for the three tiers. Reusing these singletons keeps
# FastAPI's dependency identity stable across routes.
require_viewer = require_role("viewer")
require_operator = require_role("operator")
require_admin = require_role("admin")
