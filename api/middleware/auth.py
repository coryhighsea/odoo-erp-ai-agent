"""
Authentication middleware for the Odoo ERP AI Agent API wrapper
"""
from fastapi import Request, Response, HTTPException, Depends, Header
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_403_FORBIDDEN, HTTP_429_TOO_MANY_REQUESTS
import time
import logging
import os
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import threading

# Import configuration
from config import API_KEYS, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW

# Configure logging
logger = logging.getLogger(__name__)

# API Key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Rate limiting storage
rate_limit_data = {}
rate_limit_lock = threading.Lock()

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)) -> str:
    """
    Verify that the API key is valid
    
    This function checks if the provided API key is in the list of valid API keys.
    If the key is missing or invalid, it raises an HTTP 403 Forbidden exception.
    
    Args:
        api_key: The API key from the X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If the API key is missing or invalid
    """
    if not api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="API key is missing"
        )
    
    valid_keys = API_KEYS.split(",") if API_KEYS else []
    
    if not valid_keys or api_key not in valid_keys:
        logger.warning(f"Invalid API key: {api_key[:5]}...")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key

async def rate_limit(request: Request):
    """
    Rate limiting middleware
    
    This function implements a simple rate limiting mechanism based on the client's
    IP address and API key. It limits the number of requests per time window.
    
    Args:
        request: The FastAPI request object
        
    Raises:
        HTTPException: If the rate limit is exceeded
    """
    # Get client identifier (IP + API key)
    client_ip = request.client.host if request.client else "unknown"
    api_key = request.headers.get("X-API-Key", "")
    client_id = f"{client_ip}:{api_key[:5]}"
    
    # Get current time
    current_time = time.time()
    
    # Clean up old entries
    with rate_limit_lock:
        for key in list(rate_limit_data.keys()):
            if current_time - rate_limit_data[key]["timestamp"] > RATE_LIMIT_WINDOW:
                del rate_limit_data[key]
        
        # Check rate limit
        if client_id in rate_limit_data:
            data = rate_limit_data[client_id]
            if current_time - data["timestamp"] < RATE_LIMIT_WINDOW:
                data["count"] += 1
                if data["count"] > RATE_LIMIT_REQUESTS:
                    logger.warning(f"Rate limit exceeded for client {client_id}")
                    raise HTTPException(
                        status_code=HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds."
                    )
            else:
                # Reset if window has passed
                data["timestamp"] = current_time
                data["count"] = 1
        else:
            # First request from this client
            rate_limit_data[client_id] = {
                "timestamp": current_time,
                "count": 1
            }

def start_cleanup_task():
    """
    Start a background task to clean up rate limiting data
    
    This function starts a background task that periodically cleans up
    old entries in the rate limiting data dictionary.
    """
    async def cleanup_task():
        while True:
            try:
                current_time = time.time()
                with rate_limit_lock:
                    for key in list(rate_limit_data.keys()):
                        if current_time - rate_limit_data[key]["timestamp"] > RATE_LIMIT_WINDOW * 2:
                            del rate_limit_data[key]
                await asyncio.sleep(RATE_LIMIT_WINDOW)
            except Exception as e:
                logger.error(f"Error in rate limit cleanup task: {str(e)}")
                await asyncio.sleep(RATE_LIMIT_WINDOW)
    
    # Start the cleanup task
    asyncio.create_task(cleanup_task())
