import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.deps import get_db
from app.routers.artifacts import flat_router as artifacts_flat_router
from app.routers.artifacts import nested_router as artifacts_nested_router
from app.routers.auth import limiter as auth_limiter
from app.routers.auth import router as auth_router
from app.routers.learners import flat_router as learners_flat_router
from app.routers.learners import nested_router as learners_nested_router
from app.routers.rubrics import router as rubrics_router
from app.routers.submissions import nested_router as submissions_nested_router
from app.routers.submissions import router as submissions_router
from app.routers.webhooks import router as webhooks_router
from app.services.auth_service import seed_superadmin

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db: Session = SessionLocal()
    try:
        seed_superadmin(db, settings)
    finally:
        db.close()
    yield


app = FastAPI(title="RubricIQ API", version="0.1.0", lifespan=lifespan)

app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(rubrics_router)
app.include_router(learners_nested_router)
app.include_router(learners_flat_router)
app.include_router(submissions_nested_router)
app.include_router(submissions_router)
app.include_router(artifacts_nested_router)
app.include_router(artifacts_flat_router)
app.include_router(webhooks_router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "env": settings.env}
