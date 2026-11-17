"""Entry point: creates the FastAPI app and registers all routers."""

from fastapi import APIRouter, FastAPI

from app.api.routes import catalog, glossary, health, promises, stats
from app.core.config import settings

app = FastAPI(title="Sľubomer API", version="0.1.0", debug=settings.debug)

# Each area of the API lives in its own router under app/api/routes/.
app.include_router(health.router)

# Versioned public API: /api/v1/...
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(promises.router)
api_v1.include_router(catalog.router)
api_v1.include_router(stats.router)
api_v1.include_router(glossary.router)
app.include_router(api_v1)
