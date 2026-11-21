import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from api.auth.security import Identity, require_identity
from api.db.session import get_db
from api.services import store

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/events.csv")
def export_events(
    site_id: int | None = Query(default=None),
    camera_id: str | None = Query(default=None),
    item: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    start: datetime | None = Query(default=None, alias="from"),
    end: datetime | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_identity),
) -> Response:
    del identity
    rows, _ = store.list_events(
        db, site_id, camera_id, item, status_filter, start, end, 1, 100000
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["id", "camera_id", "occurred_at", "track_id", "item", "status", "confidence",
         "model_version", "config_version", "review_state"]
    )
    for row in rows:
        writer.writerow(
            [row.id, row.camera_id, row.occurred_at.isoformat(), row.track_id, row.item,
             row.status, row.confidence, row.model_version, row.config_version, row.review_state]
        )
    return Response(content=buffer.getvalue(), media_type="text/csv")


@router.get("/counts.csv")
def export_counts(
    camera_id: str | None = Query(default=None),
    class_name: str | None = Query(default=None, alias="class"),
    start: datetime | None = Query(default=None, alias="from"),
    end: datetime | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_identity),
) -> Response:
    del identity
    rows = store.list_count_buckets(db, None, camera_id, class_name, start, end)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["camera_id", "bucket_start", "class_name", "mode", "count", "uncertain_count"])
    for row in rows:
        writer.writerow(
            [row.camera_id, row.bucket_start.isoformat(), row.class_name, row.mode,
             row.count, row.uncertain_count]
        )
    return Response(content=buffer.getvalue(), media_type="text/csv")
