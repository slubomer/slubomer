"""Entry point: creates the FastAPI app and registers all routers."""

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    admin_audit,
    admin_catalog,
    admin_promises,
    admin_users,
    admin_verdicts,
    auth,
    catalog,
    glossary,
    health,
    promises,
    stats,
)
from app.core.config import settings
from app.services.errors import ServiceError

app = FastAPI(title="Sľubomer API", version="0.1.0", debug=settings.debug)

# Browsers may call the API only from the listed origins (with the session cookie).
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )


@app.exception_handler(ServiceError)
def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """Errors from services (app/services/errors.py) become {"detail": ...} responses."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Each area of the API lives in its own router under app/api/routes/.
app.include_router(health.router)

# Versioned API: /api/v1/...
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(promises.router)
api_v1.include_router(catalog.router)
api_v1.include_router(stats.router)
api_v1.include_router(glossary.router)
api_v1.include_router(auth.router)
api_v1.include_router(admin_users.router)
api_v1.include_router(admin_audit.router)
api_v1.include_router(admin_promises.router)
api_v1.include_router(admin_catalog.router)
api_v1.include_router(admin_verdicts.router)
app.include_router(api_v1)
