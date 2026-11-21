from dataclasses import dataclass
from datetime import datetime, timedelta

from worker.health import HealthMonitor
from worker.ingest.replay import FrameSource
from worker.logic.count_events import CountEventDraft
from worker.logic.line_counter import LineCounter
from worker.logic.ppe_state_machine import ComplianceEventDraft, PPEObservation, PPEStateMachine
from worker.models.registry import PersonPPEModel, UtensilModel
from worker.pipeline.frame_types import PersonObservation, PPEPrediction
from worker.publisher.events import EventPublisher


@dataclass
class ReplayResult:
    frames_processed: int
    compliance_events: list[ComplianceEventDraft]
    count_events: list[CountEventDraft]


class ReplayEngine:
    def __init__(
        self,
        frame_source: FrameSource,
        person_model: PersonPPEModel,
        utensil_model: UtensilModel,
        state_machine: PPEStateMachine,
        line_counter: LineCounter,
        publisher: EventPublisher,
        health_monitor: HealthMonitor,
        config_version: str,
        item_regions: dict[str, str] | None = None,
        min_pixels: dict[str, float] | None = None,
    ) -> None:
        self.frame_source = frame_source
        self.person_model = person_model
        self.utensil_model = utensil_model
        self.state_machine = state_machine
        self.line_counter = line_counter
        self.publisher = publisher
        self.health_monitor = health_monitor
        self.config_version = config_version
        self.item_regions = item_regions or {
            "hair_cover": "head",
            "gloves": "hands",
            "mask": "head",
        }
        self.min_pixels = min_pixels or {
            "hair_cover": 1200.0,
            "gloves": 625.0,
            "mask": 1200.0,
        }

    def run(self) -> ReplayResult:
        compliance_events: list[ComplianceEventDraft] = []
        count_events: list[CountEventDraft] = []
        frames_processed = 0
        last_timestamp = None

        for frame in self.frame_source.frames():
            last_timestamp = frame.timestamp
            self.health_monitor.update(self.frame_source.camera_id, frame.timestamp)

            people = self.person_model.predict(frame)
            utensils = self.utensil_model.predict(frame)

            for person in people:
                for item, prediction in person.ppe.items():
                    event = self._assess_ppe(
                        frame.camera_id, person, item, prediction, frame.timestamp
                    )
                    if event is not None:
                        self.publisher.publish_compliance(event)
                        compliance_events.append(event)

            for utensil in utensils:
                if utensil.class_name not in ("cup", "plate"):
                    continue
                count_event = self.line_counter.update(
                    camera_id=frame.camera_id,
                    track_id=utensil.track_id,
                    class_name=utensil.class_name,
                    bbox=utensil.bbox,
                    timestamp=frame.timestamp,
                    confidence=utensil.confidence,
                    model_version=self.utensil_model.version,
                    config_version=self.config_version,
                )
                if count_event is not None:
                    self.publisher.publish_count(count_event)
                    count_events.append(count_event)

            frames_processed += 1

        if last_timestamp is not None:
            self.state_machine.expire(
                last_timestamp + timedelta(seconds=self.state_machine.max_stale_seconds + 1)
            )

        return ReplayResult(
            frames_processed=frames_processed,
            compliance_events=compliance_events,
            count_events=count_events,
        )

    def _assess_ppe(
        self,
        camera_id: str,
        person: PersonObservation,
        item: str,
        prediction: PPEPrediction,
        timestamp: datetime,
    ) -> ComplianceEventDraft | None:
        region_name = self.item_regions.get(item, item)
        region = next((r for r in person.regions if r.name == region_name), None)
        observation = PPEObservation(
            item=item,
            state=prediction.state,
            confidence=prediction.confidence,
            region_visible=region is not None
            and region.visibility in ("visible", "partly_visible"),
            min_pixel_ok=region is not None
            and region.area_pixels >= self.min_pixels.get(item, 0.0),
            timestamp=timestamp,
        )
        return self.state_machine.observe(
            camera_id=camera_id,
            track_id=person.track_id,
            observation=observation,
            model_version=self.person_model.version,
            config_version=self.config_version,
        )
