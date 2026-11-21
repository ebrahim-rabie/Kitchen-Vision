from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.auth.security import Identity, require_identity, require_reviewer
from api.config import settings
from api.db.models import ComplianceEvent
from api.db.session import get_db
from api.schemas import EventOut, Page, ReviewIn
from api.services import store

router = APIRouter(prefix="/events", tags=["events"])
evidence_router = APIRouter(tags=["evidence"])


@router.get("", response_model=Page[EventOut])
def list_events(
    site_id: int | None = Query(default=None),
    camera_id: str | None = Query(default=None),
    item: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    start: datetime | None = Query(default=None, alias="from"),
    end: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_identity),
) -> Page[ComplianceEvent]:
    del identity
    rows, total = store.list_events(
        db, site_id, camera_id, item, status_filter, start, end, page, page_size
    )
    return Page(items=rows, total=total, page=page, page_size=page_size)


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_identity),
) -> EventOut:
    del identity
    event = store.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.post("/{event_id}/review", response_model=EventOut)
def review_event(
    event_id: str,
    payload: ReviewIn,
    db: Session = Depends(get_db),
    reviewer: Identity = Depends(require_reviewer),
) -> EventOut:
    event = store.review_event(
        db, event_id, reviewer.name, payload.disposition, payload.reason
    )
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@evidence_router.get("/evidence/{opaque_key}")
def evidence(opaque_key: str, identity: Identity = Depends(require_identity)) -> dict[str, object]:
    del identity
    return {
        "opaque_key": opaque_key,
        "expires_in": settings.EVIDENCE_URL_TTL_SECONDS,
        "content_url": f"/api/v1/evidence/content/{opaque_key}",
    }
