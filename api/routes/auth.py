from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth.security import Identity, require_identity
from api.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginIn, identity: Identity = Depends(require_identity)) -> dict[str, str]:
    return {
        "access_token": settings.API_KEY,
        "token_type": "bearer",
        "expires_in": str(settings.TOKEN_TTL_SECONDS),
        "subject": identity.name,
        "username": payload.username,
    }
