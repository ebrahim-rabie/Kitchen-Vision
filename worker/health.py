from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

CameraState = Literal["online", "offline", "degraded"]


@dataclass
class CameraHealth:
    camera_id: str
    state: CameraState = "offline"
    last_frame_at: datetime | None = None
    last_update_at: datetime | None = None
    reconnect_attempts: int = 0
    stale_frames_dropped: int = 0


class HealthMonitor:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._cameras: dict[str, CameraHealth] = {}

    def register(self, camera_id: str) -> CameraHealth:
        return self._cameras.setdefault(camera_id, CameraHealth(camera_id=camera_id))

    def update(self, camera_id: str, timestamp: datetime, stale: bool = False) -> None:
        health = self.register(camera_id)
        health.last_frame_at = timestamp
        health.last_update_at = timestamp
        health.state = "degraded" if stale else "online"
        if stale:
            health.stale_frames_dropped += 1

    def record_reconnect(self, camera_id: str) -> None:
        health = self.register(camera_id)
        health.reconnect_attempts += 1
        health.state = "degraded"

    def expire(self, now: datetime) -> list[CameraHealth]:
        transitions: list[CameraHealth] = []
        for health in self._cameras.values():
            if health.last_update_at is None:
                continue
            if now - health.last_update_at > timedelta(seconds=self.timeout_seconds):
                if health.state != "offline":
                    health.state = "offline"
                    transitions.append(health)
        return transitions

    def get(self, camera_id: str) -> CameraHealth:
        return self.register(camera_id)

    def all(self) -> list[CameraHealth]:
        return list(self._cameras.values())
