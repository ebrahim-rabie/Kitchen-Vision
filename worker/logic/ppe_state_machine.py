from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from worker.logic.ids import idempotency_key
from worker.pipeline.frame_types import PPEState

EventStatus = Literal["compliant", "violation"]
StateName = Literal[
    "UNKNOWN", "OBSERVING", "SUSPECTED", "COMPLIANT", "VIOLATION", "COOLDOWN", "UNCLEAR"
]


@dataclass(frozen=True)
class PPEObservation:
    item: str
    state: PPEState
    confidence: float
    region_visible: bool
    min_pixel_ok: bool
    timestamp: datetime


@dataclass(frozen=True)
class ComplianceEventDraft:
    camera_id: str
    track_id: str
    item: str
    status: EventStatus
    occurred_at: datetime
    confidence: float
    model_version: str
    config_version: str
    idempotency_key: str


@dataclass
class _TrackState:
    name: StateName = "UNKNOWN"
    since: datetime | None = None
    absent_since: datetime | None = None
    present_since: datetime | None = None
    cooldown_until: datetime | None = None
    last_seen: datetime | None = None
    confidence: float = 0.0


class PPEStateMachine:
    def __init__(
        self,
        min_confidence: float = 0.6,
        min_evidence_seconds: float = 2.0,
        grace_seconds: float = 3.0,
        cooldown_seconds: float = 30.0,
        max_stale_seconds: float = 5.0,
    ) -> None:
        self.min_confidence = min_confidence
        self.min_evidence_seconds = min_evidence_seconds
        self.grace_seconds = grace_seconds
        self.cooldown_seconds = cooldown_seconds
        self.max_stale_seconds = max_stale_seconds
        self._states: dict[tuple[str, str, str], _TrackState] = {}

    def observe(
        self,
        camera_id: str,
        track_id: str,
        observation: PPEObservation,
        model_version: str,
        config_version: str,
    ) -> ComplianceEventDraft | None:
        key = (camera_id, track_id, observation.item)
        state = self._states.setdefault(key, _TrackState())
        now = observation.timestamp
        state.last_seen = now

        if state.since is None:
            state.since = now
            state.name = "OBSERVING"

        if state.name == "COOLDOWN" and state.cooldown_until and now < state.cooldown_until:
            return None

        if state.name == "COOLDOWN":
            state.name = "OBSERVING"
            state.since = now
            state.absent_since = None
            state.present_since = None
            state.cooldown_until = None

        assessable = (
            observation.region_visible
            and observation.min_pixel_ok
            and observation.state not in ("not_assessable", "not_applicable")
            and observation.confidence >= self.min_confidence
        )
        if not assessable:
            if state.name != "UNCLEAR":
                state.name = "UNCLEAR"
                state.since = now
                state.absent_since = None
                state.present_since = None
            return None

        state.confidence = observation.confidence

        if observation.state == "present":
            state.present_since = state.present_since or now
            state.absent_since = None
            if (
                state.name != "COMPLIANT"
                and (now - state.present_since).total_seconds() >= self.min_evidence_seconds
            ):
                state.name = "COMPLIANT"
                state.since = now
                return self._event(
                    camera_id,
                    track_id,
                    observation.item,
                    "compliant",
                    state.present_since,
                    observation.confidence,
                    model_version,
                    config_version,
                )
            return None

        if observation.state == "absent":
            if state.name in ("UNKNOWN", "OBSERVING", "UNCLEAR", "COMPLIANT"):
                state.name = "SUSPECTED"
                state.since = now
                state.absent_since = state.absent_since or now
                state.present_since = None
            if (
                state.name == "SUSPECTED"
                and state.absent_since is not None
                and (now - state.absent_since).total_seconds() >= self.grace_seconds
            ):
                occurred_at = state.absent_since
                confidence = state.confidence
                state.name = "COOLDOWN"
                state.since = now
                state.cooldown_until = now + timedelta(seconds=self.cooldown_seconds)
                state.absent_since = None
                return self._event(
                    camera_id,
                    track_id,
                    observation.item,
                    "violation",
                    occurred_at,
                    confidence,
                    model_version,
                    config_version,
                )

        return None

    def expire(self, now: datetime) -> None:
        for state in self._states.values():
            if state.name == "COOLDOWN":
                continue
            if state.last_seen is None:
                continue
            if (now - state.last_seen).total_seconds() > self.max_stale_seconds:
                state.name = "UNCLEAR"
                state.since = now
                state.absent_since = None
                state.present_since = None

    def reset_track(self, camera_id: str, track_id: str) -> None:
        for key in list(self._states):
            if key[0] == camera_id and key[1] == track_id:
                del self._states[key]

    def state_of(self, camera_id: str, track_id: str, item: str) -> StateName:
        return self._states.get((camera_id, track_id, item), _TrackState()).name

    def _event(
        self,
        camera_id: str,
        track_id: str,
        item: str,
        status: EventStatus,
        occurred_at: datetime,
        confidence: float,
        model_version: str,
        config_version: str,
    ) -> ComplianceEventDraft:
        return ComplianceEventDraft(
            camera_id=camera_id,
            track_id=track_id,
            item=item,
            status=status,
            occurred_at=occurred_at,
            confidence=confidence,
            model_version=model_version,
            config_version=config_version,
            idempotency_key=idempotency_key(
                camera_id, track_id, item, status, occurred_at.isoformat(),
                model_version, config_version
            ),
        )
