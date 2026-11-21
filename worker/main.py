import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from worker.health import HealthMonitor
from worker.ingest.replay import SyntheticFrameSource
from worker.logic.line_counter import Line, LineCounter, Point
from worker.logic.ppe_state_machine import PPEStateMachine
from worker.models.mock_models import MockPersonPPEModel, MockUtensilModel
from worker.publisher.events import JsonlPublisher
from worker.replay import ReplayEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay synthetic kitchen vision data")
    parser.add_argument("--camera-id", default="cam-pilot-01")
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--fps", type=float, default=5.0)
    parser.add_argument("--config-version", default="rules-v1")
    parser.add_argument("--output", type=Path, default=Path("data/events.jsonl"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = datetime.now(timezone.utc).replace(microsecond=0)
    source = SyntheticFrameSource(args.camera_id, start, args.duration, args.fps)
    person_model = MockPersonPPEModel(start)
    utensil_model = MockUtensilModel(start)
    state_machine = PPEStateMachine()
    line_counter = LineCounter(
        line=Line(Point(0.0, 0.0), Point(100.0, 0.0)),
        direction="positive",
        stability_seconds=0.5,
    )
    publisher = JsonlPublisher(args.output)
    health = HealthMonitor()
    engine = ReplayEngine(
        frame_source=source,
        person_model=person_model,
        utensil_model=utensil_model,
        state_machine=state_machine,
        line_counter=line_counter,
        publisher=publisher,
        health_monitor=health,
        config_version=args.config_version,
    )
    result = engine.run()
    summary = {
        "frames_processed": result.frames_processed,
        "compliance_events": [asdict(event) for event in result.compliance_events],
        "count_events": [asdict(event) for event in result.count_events],
        "camera_health": asdict(health.get(args.camera_id)),
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
