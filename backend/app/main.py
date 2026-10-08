import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import engine, init_db
from app.core.exceptions import AppException

# Import Routers
from app.auth.router import router as auth_router
from app.employees.router import router as employees_router
from app.breakfast.router import router as breakfast_router
from app.breakfast.money_router import router as breakfast_money_router, finance_router
from app.breakfast.settings_router import router as settings_router
from app.breakfast.holiday_router import router as holiday_router
from app.breakfast.order_router import router as order_router
from app.reports.router import router as reports_router
from app.audit.router import router as audit_router
from app.notifications.router import router as notifications_router
from app.users.router import router as users_router
from app.modules.router import router as modules_router
from app.breakfast.memberships_router import router as bms_memberships_router

from app.core.init_roles import ensure_roles_and_permissions
from app.core.init_modules import ensure_modules_and_memberships

logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing REVY Enterprise application...")
    init_db()
    ensure_roles_and_permissions()
    ensure_modules_and_memberships()
    yield
    logger.info("Shutting down REVY Enterprise application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^(https://[a-zA-Z0-9_-]+\.vercel\.app|http://(localhost|127\.0\.0\.1)(:\d+)?)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    content = {
        "success": False,
        "message": exc.message,
        "error_code": exc.error_code,
        "details": exc.details,
        **exc.extra_fields
    }
    return JSONResponse(status_code=exc.status_code, content=content)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0]["msg"] if errors else "Invalid request data"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": first_error,
            "error_code": "VALIDATION_ERROR",
            "details": errors
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal Server Error. Please contact administrator.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )

# Health Check Endpoints
@app.get("/api/health")
@app.get("/api/v1/health")
def health_check():
    is_connected = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            is_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    if not is_connected:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "status": "unhealthy",
                "database": "disconnected",
                "message": "Database connection is unavailable"
            }
        )

    return {
        "success": True,
        "status": "healthy",
        "database": "connected"
    }

from app.modules.services_router import (
    crm_router,
    lms_router,
    ims_router,
    leave_router,
    mis_router,
    dwr_router
)

# Register Routers under both /api/v1 and /api for full backward compatibility
for prefix in ["/api/v1", "/api"]:
    app.include_router(auth_router, prefix=prefix)
    app.include_router(employees_router, prefix=prefix)
    app.include_router(breakfast_money_router, prefix=prefix)
    app.include_router(breakfast_router, prefix=prefix)
    app.include_router(reports_router, prefix=prefix)
    app.include_router(audit_router, prefix=prefix)
    app.include_router(settings_router, prefix=prefix)
    app.include_router(holiday_router, prefix=prefix)
    app.include_router(order_router, prefix=prefix)
    app.include_router(notifications_router, prefix=prefix)
    app.include_router(finance_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    app.include_router(modules_router, prefix=prefix)
    app.include_router(bms_memberships_router, prefix=prefix)
    app.include_router(crm_router, prefix=prefix)
    app.include_router(lms_router, prefix=prefix)
    app.include_router(ims_router, prefix=prefix)
    app.include_router(leave_router, prefix=prefix)
    app.include_router(mis_router, prefix=prefix)
    app.include_router(dwr_router, prefix=prefix)

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 5001))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
