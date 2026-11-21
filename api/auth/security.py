from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from api.config import settings


@dataclass(frozen=True)
class Identity:
    name: str
    role: str


def require_identity(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    x_role: str = Header(default="viewer"),
) -> Identity:
    token = x_api_key
    if token is None and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if token != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API credential",
        )
    return Identity(name="api-key", role=x_role)


def require_reviewer(identity: Identity = Depends(require_identity)) -> Identity:
    if identity.role not in ("reviewer", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewer role required")
    return identity


def require_admin(identity: Identity = Depends(require_identity)) -> Identity:
    if identity.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return identity
