from datetime import datetime, timezone


def run_pending_schedules() -> list[str]:
    return []


def next_run_at(recurrence: str) -> datetime:
    return datetime.now(timezone.utc)
