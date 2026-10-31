"""Entry point: creates the FastAPI app and registers all routers."""

from fastapi import FastAPI

from app.api.routes import health
from app.core.config import settings

app = FastAPI(title="Sľubomer API", version="0.1.0", debug=settings.debug)

# Each area of the API lives in its own router under app/api/routes/.
app.include_router(health.router)
