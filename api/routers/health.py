from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
import time
import os
import platform
import psutil
import logging
from datetime import datetime, timedelta
import xmlrpc.client
import requests

# Import configuration
from config import API_VERSION, ENVIRONMENT

from api.models.responses import HealthStatus, HealthCheckResponse
from api.middleware.auth import verify_api_key

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/health", tags=["System"])

# Application start time
START_TIME = datetime.now()


@router.get("", response_model=None)
async def health_check():
    """
    Health check endpoint
    
    This endpoint checks the health of the API and its components.
    """
    # Check components health
    components = {
        "api": HealthStatus.OK,
        "agent": check_agent_health(),
        "odoo": check_odoo_health(),
        "system": check_system_health()
    }
    
    # Determine overall status
    overall_status = HealthStatus.OK
    if HealthStatus.ERROR in components.values():
        overall_status = HealthStatus.ERROR
    elif HealthStatus.DEGRADED in components.values():
        overall_status = HealthStatus.DEGRADED
    
    # Get uptime
    uptime_seconds = (datetime.now() - START_TIME).total_seconds()
    
    # Return health check response as a dictionary with manually serialized datetime
    return {
        "status": overall_status,
        "version": API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "components": components,
        "details": {
            "uptime_seconds": uptime_seconds,
            "environment": ENVIRONMENT,
            "host": platform.node()
        }
    }


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint
    
    This endpoint returns a simple response to check if the API is running.
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@router.get("/detailed", dependencies=[Depends(verify_api_key)])
async def detailed_health():
    """
    Detailed health check endpoint
    
    This endpoint returns detailed health information about the API and its components.
    Requires API key authentication.
    """
    # Get basic health check
    health = await health_check()
    
    # Add detailed system information
    system_info = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "cpu_usage": psutil.cpu_percent(interval=0.1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "free": psutil.disk_usage('/').free,
            "percent": psutil.disk_usage('/').percent
        },
        "uptime": str(datetime.now() - START_TIME)
    }
    
    # Add environment information
    env_info = {
        "api_host": os.getenv("API_HOST", "0.0.0.0"),
        "api_port": os.getenv("API_PORT", "8080"),
        "log_level": os.getenv("LOG_LEVEL", "info"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }
    
    # Return detailed health information
    return {
        "health": health.dict(),
        "system": system_info,
        "environment": env_info
    }


def check_agent_health() -> HealthStatus:
    """Check the health of the AI agent component"""
    try:
        # Get agent URL from environment
        agent_url = os.getenv("AI_AGENT_URL", "http://localhost:8000")
        
        # Try to connect to agent
        response = requests.get(f"{agent_url}/ping", timeout=2)
        
        if response.status_code == 200:
            return HealthStatus.OK
        else:
            logger.warning(f"Agent health check failed with status code: {response.status_code}")
            return HealthStatus.DEGRADED
    except requests.exceptions.RequestException as e:
        logger.error(f"Agent health check failed: {str(e)}")
        return HealthStatus.ERROR


def check_odoo_health() -> HealthStatus:
    """Check the health of the Odoo connection"""
    try:
        # Get Odoo connection details from environment
        odoo_url = os.getenv("ODOO_URL", "http://localhost:8069")
        odoo_db = os.getenv("ODOO_DB", "odoo")
        odoo_user = os.getenv("ODOO_USERNAME", "admin")
        odoo_password = os.getenv("ODOO_PASSWORD", "admin")
        
        # Try to connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
        version_info = common.version()
        
        # Try to authenticate
        uid = common.authenticate(odoo_db, odoo_user, odoo_password, {})
        
        if uid:
            return HealthStatus.OK
        else:
            logger.warning("Odoo health check failed: Authentication failed")
            return HealthStatus.DEGRADED
    except Exception as e:
        logger.error(f"Odoo health check failed: {str(e)}")
        return HealthStatus.ERROR


def check_system_health() -> HealthStatus:
    """Check the health of the system"""
    try:
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Check memory usage
        memory_percent = psutil.virtual_memory().percent
        
        # Check disk usage
        disk_percent = psutil.disk_usage('/').percent
        
        # Determine status based on resource usage
        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            logger.warning(f"System resources critical: CPU={cpu_percent}%, Memory={memory_percent}%, Disk={disk_percent}%")
            return HealthStatus.ERROR
        elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 70:
            logger.info(f"System resources high: CPU={cpu_percent}%, Memory={memory_percent}%, Disk={disk_percent}%")
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.OK
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        return HealthStatus.ERROR


def get_health_details() -> Dict[str, Any]:
    """Get detailed health information"""
    uptime = datetime.now() - START_TIME
    
    return {
        "uptime": str(uptime),
        "uptime_seconds": uptime.total_seconds(),
        "started_at": START_TIME.isoformat(),
        "hostname": platform.node(),
        "cpu_usage": psutil.cpu_percent(interval=0.1),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }
