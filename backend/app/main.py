from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import engine
from app.routers.auth import router as auth_router
from app.routers.needs import router as needs_router
from app.routers.matches import router as matches_router
from app.routers.donations import router as donations_router
from app.routers.schools import admin_router as admin_router
from app.routers.schools import router as schools_router

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(needs_router, prefix=settings.api_prefix)
app.include_router(matches_router, prefix=settings.api_prefix)
app.include_router(donations_router, prefix=settings.api_prefix)
app.include_router(schools_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready")
def ready() -> dict[str, str]:
    if not settings.database_url:
        return {"status": "degraded", "database": "not_configured"}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "degraded", "database": "unavailable"}

    return {"status": "ready", "database": "ok"}
