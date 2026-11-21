from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CameraOut(OrmModel):
    id: str
    site_id: int
    name: str
    active: bool
    resolution: str | None = None
    fps: float | None = None
    sampling_profile: str | None = None


class EventOut(OrmModel):
    id: str
    camera_id: str
    occurred_at: datetime
    track_id: str
    item: str
    status: str
    confidence: float
    model_version: str
    config_version: str
    review_state: str


class ReviewIn(BaseModel):
    reviewer: str
    disposition: str
    reason: str | None = None


class CountEventOut(OrmModel):
    id: str
    camera_id: str
    occurred_at: datetime
    class_name: str
    mode: str
    direction: str
    count: int
    confidence: float


class CountSummary(OrmModel):
    camera_id: str
    class_name: str
    bucket_start: datetime
    count: int
    uncertain_count: int
    mode: str


class HealthOut(OrmModel):
    camera_id: str
    state: str
    occurred_at: datetime
    reason: str | None = None


class ScheduleIn(BaseModel):
    id: str
    owner: str
    recipient_ref: str
    timezone: str = "UTC"
    recurrence: str
    filters: dict[str, object] = {}
    enabled: bool = True
    channel: str = "email"


class ScheduleOut(OrmModel):
    id: str
    owner: str
    channel: str
    recipient_ref: str
    timezone: str
    recurrence: str
    filters_json: str
    enabled: bool


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T]
    total: int
    page: int
    page_size: int
