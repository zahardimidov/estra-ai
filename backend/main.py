import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import setup_logging
from infrastructure.db.session import run_database
from infrastructure.monitoring.metrics_api import request_count, request_latency

setup_logging()
logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        path = route.path if route else request.url.path

        request_count.labels(request.method, path, response.status_code).inc()
        request_latency.labels(request.method, path).observe(duration)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting up... {app.title} ...")
    await run_database()
    logger.info("Database is ready")
    yield
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="EstraAI",
        description="AI-powered content moderation API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    from api.v1 import router as router_v1

    app.include_router(router_v1)

    return app


app = create_app()
