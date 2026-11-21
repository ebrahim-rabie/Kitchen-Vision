from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.db.session import init_db
from api.routes import auth, cameras, counts, events, exports, health, report_schedules
from api.services.store import seed_demo_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from api.db.session import SessionLocal

    with SessionLocal() as session:
        seed_demo_data(session)
    yield


app = FastAPI(
    title="Kitchen Vision API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(events.evidence_router, prefix="/api/v1")
app.include_router(counts.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(report_schedules.router, prefix="/api/v1")
