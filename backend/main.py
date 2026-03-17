from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1 import api_router
from app.db.database import create_tables
from app.core.security import get_password_hash
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up LLM Eval Platform...")
    await create_tables()
    await _create_default_admin()
    yield
    # Shutdown
    logger.info("Shutting down...")


async def _create_default_admin():
    """Create default admin user if not exists."""
    from app.db.database import async_session_maker
    from app.db.models import User
    from sqlalchemy import select

    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin = User(
                username="admin",
                email="admin@llmeval.local",
                hashed_password=get_password_hash("admin123"),
                full_name="System Admin",
                is_admin=True,
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            logger.info("Default admin user created: admin / admin123")


app = FastAPI(
    title="LLM Evaluation Platform API",
    description="Enterprise-grade LLM evaluation platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_slow_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if elapsed_ms > 500:  # Log requests slower than 500ms
        logger.warning(
            "SLOW REQUEST: %s %s took %.0fms",
            request.method, request.url.path, elapsed_ms,
        )
    return response


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
