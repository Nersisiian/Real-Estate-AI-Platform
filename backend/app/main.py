from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.middleware.observability import RequestTracingMiddleware
from app.presentation.api.v1 import chat, search, recommend, health, admin
from app.presentation.api.error_handlers import register_exception_handlers

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    yield
    logger.info("Shutting down application...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestTracingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.DEBUG else settings.ALLOWED_ORIGINS,
    )

    register_exception_handlers(app)

    api_prefix = settings.API_V1_PREFIX
    app.include_router(chat.router, prefix=api_prefix, tags=["chat"])
    app.include_router(search.router, prefix=api_prefix, tags=["search"])
    app.include_router(recommend.router, prefix=api_prefix, tags=["recommend"])
    app.include_router(health.router, prefix=api_prefix, tags=["health"])
    app.include_router(admin.router, prefix=api_prefix, tags=["admin"])

    @app.get("/")
    async def root():
        return {"message": f"Welcome to {settings.APP_NAME} API"}

    return app


app = create_app()