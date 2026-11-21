from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.auth.security import Identity, require_identity
from api.db.models import Camera, CameraHealthEvent
from api.db.session import get_db
from api.schemas import CameraOut, HealthOut, Page
from api.services import store

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=Page[CameraOut])
def list_cameras(
    site_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_identity),
) -> Page[Camera]:
    del identity
    rows = store.list_cameras(db, site_id, status)
    return Page(items=rows, total=len(rows), page=1, page_size=len(rows) or 1)


@router.get("/{camera_id}/health", response_model=list[HealthOut])
def camera_health(
    camera_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_identity),
) -> list[CameraHealthEvent]:
    del identity
    return store.list_camera_health(db, camera_id)
