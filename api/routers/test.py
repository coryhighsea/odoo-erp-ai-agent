"""
Test router for debugging API issues
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
from api.middleware.auth import verify_api_key

# Initialize router
router = APIRouter(prefix="/test", tags=["Test"])

@router.post("/echo")
async def echo_post(
    data: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """
    Simple echo endpoint that returns the data it receives
    """
    return {
        "success": True,
        "message": "Echo successful",
        "data": data
    }

@router.get("/ping")
async def ping():
    """
    Simple ping endpoint
    """
    return {
        "success": True,
        "message": "pong"
    }

@router.get("/simple")
async def simple():
    """
    Simple endpoint without authentication
    """
    return {
        "success": True,
        "message": "Hello, world!"
    }
