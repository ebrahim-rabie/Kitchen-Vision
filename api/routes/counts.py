from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.auth.security import Identity, require_identity
from api.db.models import CountBucket
from api.db.session import get_db
from api.schemas import CountSummary
from api.services import store

router = APIRouter(prefix="/counts", tags=["counts"])


@router.get("/summary", response_model=list[CountSummary])
@router.get("/series", response_model=list[CountSummary])
def counts(
    site_id: int | None = Query(default=None),
    camera_id: str | None = Query(default=None),
    class_name: str | None = Query(default=None, alias="class"),
    bucket: str | None = Query(default=None),
    start: datetime | None = Query(default=None, alias="from"),
    end: datetime | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_identity),
) -> list[CountBucket]:
    del identity, bucket
    return store.list_count_buckets(db, site_id, camera_id, class_name, start, end)
