from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from worker.pipeline.frame_types import Frame


class FrameSource(Protocol):
    camera_id: str

    def frames(self) -> Iterator[Frame]: ...


class SyntheticFrameSource:
    def __init__(
        self,
        camera_id: str,
        start: datetime,
        duration_seconds: float = 30.0,
        fps: float = 5.0,
    ) -> None:
        self.camera_id = camera_id
        self.start = start
        self.duration_seconds = duration_seconds
        self.fps = fps

    def frames(self) -> Iterator[Frame]:
        count = int(self.duration_seconds * self.fps)
        for index in range(count):
            timestamp = self.start + timedelta(seconds=index / self.fps)
            yield Frame(camera_id=self.camera_id, timestamp=timestamp)


class VideoFrameSource:
    def __init__(self, camera_id: str, path: Path, fps: float = 5.0) -> None:
        self.camera_id = camera_id
        self.path = path
        self.fps = fps

    def frames(self) -> Iterator[Frame]:
        import cv2

        capture = cv2.VideoCapture(str(self.path))
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open video: {self.path}")
        source_fps = capture.get(cv2.CAP_PROP_FPS) or self.fps
        step = max(source_fps / self.fps, 1.0)
        frame_index = 0
        try:
            while True:
                ok, image = capture.read()
                if not ok:
                    break
                if frame_index % int(step) == 0:
                    timestamp = datetime.fromtimestamp(
                        capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                    )
                    yield Frame(camera_id=self.camera_id, timestamp=timestamp, image=image)
                frame_index += 1
        finally:
            capture.release()
