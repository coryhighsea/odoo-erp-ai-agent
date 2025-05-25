from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

def setup_cors(app: FastAPI):
    """Configure CORS middleware for the application"""
    # Get allowed origins from environment variable
    origins_env = os.getenv("CORS_ORIGINS", "http://localhost:8069,http://localhost:3000")
    origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
    
    # Log CORS configuration
    logger.info(f"Configuring CORS with allowed origins: {origins}")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time", "X-API-Version"],
        max_age=600  # 10 minutes cache for preflight requests
    )
    
    return app
