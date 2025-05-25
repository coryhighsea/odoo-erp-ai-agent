#!/usr/bin/env python3
"""
Main entry point for the Odoo ERP AI Agent API wrapper
"""
import uvicorn
import os
import logging
from dotenv import load_dotenv
from api.middleware.logging import setup_logging

# Load environment variables
load_dotenv()

# Load configuration from config.py
from config import (
    API_HOST, API_PORT, API_RELOAD, LOG_LEVEL, 
    API_VERSION, ENVIRONMENT
)

# Configure logging
logger = setup_logging()

if __name__ == "__main__":
    logger.info(f"Starting Odoo ERP AI Agent API wrapper v{API_VERSION} on {API_HOST}:{API_PORT}")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"API documentation available at http://{API_HOST}:{API_PORT}/docs")
    
    uvicorn.run(
        "api.app:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
        log_level=LOG_LEVEL.lower()
    )
