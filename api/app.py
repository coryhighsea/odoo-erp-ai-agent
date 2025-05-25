"""
Main FastAPI application for the Odoo ERP AI Agent API wrapper
"""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
import time
import uuid
import logging
from datetime import datetime
import os
from typing import Callable, Dict, Any

# Import configuration
from config import (
    API_VERSION, API_PREFIX, ENVIRONMENT, CORS_ORIGINS,
    FEATURE_BATCH_OPERATIONS, FEATURE_WEBHOOKS, FEATURE_ASYNC_OPERATIONS
)

# Import routers
from api.routers import agent, odoo, health, test

# Import middleware
from api.middleware.auth import verify_api_key, rate_limit, start_cleanup_task
from api.middleware.logging import RequestLoggingMiddleware
from api.middleware.cors import setup_cors

# Import models
from api.models.responses import ErrorResponse

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Odoo ERP AI Agent API",
    description="REST API wrapper for Odoo ERP AI Agent",
    version=API_VERSION,
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
    openapi_url=f"{API_PREFIX}/openapi.json"
)

# Configure CORS
setup_cors(app)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Request ID middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    """Add request ID and processing time to response headers"""
    # Generate request ID if not present
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # Add request ID to request state
    request.state.request_id = request_id
    
    # Process request
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Add headers to response
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.6f}"
    response.headers["X-API-Version"] = API_VERSION
    
    return response

# Register routers with prefix
app.include_router(agent.router, prefix=f"{API_PREFIX}/agent")
app.include_router(odoo.router, prefix=f"{API_PREFIX}/odoo")
app.include_router(health.router, prefix=f"{API_PREFIX}/health")
app.include_router(test.router, prefix=f"{API_PREFIX}/test")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Odoo ERP AI Agent API",
        "version": API_VERSION,
        "environment": ENVIRONMENT,
        "docs_url": f"{API_PREFIX}/docs",
        "health_url": f"{API_PREFIX}/health"
    }

# Custom OpenAPI docs
@app.get(f"{API_PREFIX}/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI documentation"""
    return get_swagger_ui_html(
        openapi_url=f"{API_PREFIX}/openapi.json",
        title="Odoo ERP AI Agent API",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

# ReDoc documentation
@app.get(f"{API_PREFIX}/redoc", include_in_schema=False)
async def redoc_html():
    """ReDoc documentation"""
    return get_redoc_html(
        openapi_url=f"{API_PREFIX}/openapi.json",
        title="Odoo ERP AI Agent API",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

# Custom OpenAPI schema
@app.get(f"{API_PREFIX}/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    """OpenAPI schema"""
    return get_openapi(
        title="Odoo ERP AI Agent API",
        version=API_VERSION,
        description="REST API wrapper for Odoo ERP AI Agent",
        routes=app.routes,
    )

# Webhook endpoint for async operations
if FEATURE_WEBHOOKS:
    @app.post(f"{API_PREFIX}/webhooks/{{webhook_id}}", tags=["System"])
    async def webhook_handler(
        webhook_id: str,
        request: Request,
        api_key: str = Depends(verify_api_key)
    ):
        """
        Webhook handler for async operations
        
        This endpoint receives webhook callbacks for asynchronous operations.
        """
        # Get request body
        body = await request.json()
        
        # Log webhook event
        logger.info(f"Received webhook {webhook_id}: {body}")
        
        # Process webhook (placeholder)
        # In a real implementation, this would trigger appropriate actions
        
        return {
            "success": True,
            "webhook_id": webhook_id,
            "received_at": datetime.now().isoformat()
        }

# Error handlers
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    logger.error(f"404 error: {request.url.path}")
    error_response = ErrorResponse(
        status_code=404,
        error="Not Found",
        message=f"The requested URL {request.url.path} was not found",
        timestamp=datetime.now(),
        trace_id=getattr(request.state, "request_id", str(uuid.uuid4()))
    )
    return JSONResponse(status_code=404, content=error_response.model_dump())

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    if isinstance(exc.detail, dict) and "status_code" in exc.detail:
        # If detail is already formatted as an error response
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    
    error_response = ErrorResponse(
        status_code=exc.status_code,
        error=type(exc).__name__,
        message=str(exc.detail),
        timestamp=datetime.now(),
        trace_id=getattr(request.state, "request_id", str(uuid.uuid4()))
    )
    return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception in {request.url.path}: {str(exc)}", exc_info=True)
    
    # Get detailed exception information
    import traceback
    tb_str = traceback.format_exception(type(exc), exc, exc.__traceback__)
    logger.error(f"Traceback: {''.join(tb_str)}")
    
    error_response = ErrorResponse(
        status_code=500,
        error="Internal Server Error",
        message=str(exc),
        timestamp=datetime.now(),
        trace_id=getattr(request.state, "request_id", str(uuid.uuid4()))
    )
    return JSONResponse(status_code=500, content=error_response.model_dump())

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(f"Starting Odoo ERP AI Agent API v{API_VERSION}")
    
    # Start rate limit cleanup task
    start_cleanup_task()
    
    # Log feature flags
    logger.info(f"Feature flags: batch_operations={FEATURE_BATCH_OPERATIONS}, "
                f"webhooks={FEATURE_WEBHOOKS}, "
                f"async_operations={FEATURE_ASYNC_OPERATIONS}")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down Odoo ERP AI Agent API")
