import time
import uuid
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, Generic
from datetime import datetime, timezone
import xmlrpc.client
import requests
from functools import wraps
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar('T')


def timed_execution(func):
    """Decorator to measure execution time of functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        return result, execution_time
    return wrapper


async def timed_execution_async(func):
    """Decorator to measure execution time of async functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        execution_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        return result, execution_time
    return wrapper


def generate_trace_id() -> str:
    """Generate a unique trace ID for request tracking"""
    return str(uuid.uuid4())


def format_error_response(status_code: int, error: str, message: str, 
                         details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format a standardized error response"""
    return {
        "status_code": status_code,
        "error": error,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": generate_trace_id(),
        "details": details
    }


def create_paginated_response(items: List[T], page: int, page_size: int, 
                             total_items: int) -> Dict[str, Any]:
    """Create a standardized paginated response"""
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
    
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


def safe_json_serialize(obj: Any) -> Any:
    """Safely serialize objects to JSON, handling non-serializable types"""
    if isinstance(obj, (datetime, )):
        return obj.isoformat()
    elif isinstance(obj, (bytes, bytearray)):
        return obj.decode('utf-8', errors='replace')
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    elif hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
        return obj.to_dict()
    else:
        return str(obj)


def retry_operation(max_retries: int = 3, delay: float = 1.0, 
                   backoff_factor: float = 2.0, exceptions: Tuple = (Exception,)):
    """Decorator for retrying operations that might fail temporarily"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        sleep_time = delay * (backoff_factor ** (attempt - 1))
                        logger.warning(
                            f"Retry {attempt}/{max_retries} for {func.__name__} "
                            f"after {sleep_time:.2f}s due to: {str(e)}"
                        )
                        time.sleep(sleep_time)
            
            # If we get here, all retries failed
            logger.error(f"All {max_retries} retries failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


async def retry_operation_async(max_retries: int = 3, delay: float = 1.0, 
                              backoff_factor: float = 2.0, exceptions: Tuple = (Exception,)):
    """Decorator for retrying async operations that might fail temporarily"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        sleep_time = delay * (backoff_factor ** (attempt - 1))
                        logger.warning(
                            f"Retry {attempt}/{max_retries} for {func.__name__} "
                            f"after {sleep_time:.2f}s due to: {str(e)}"
                        )
                        await asyncio.sleep(sleep_time)
            
            # If we get here, all retries failed
            logger.error(f"All {max_retries} retries failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to a maximum length, adding a suffix if truncated"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_odoo_domain(domain_str: str) -> List:
    """Parse a string representation of an Odoo domain into a domain list"""
    try:
        # Try to parse as JSON
        domain = json.loads(domain_str)
        if isinstance(domain, list):
            return domain
    except json.JSONDecodeError:
        # If not valid JSON, try to parse as Python literal
        try:
            import ast
            domain = ast.literal_eval(domain_str)
            if isinstance(domain, list):
                return domain
        except (SyntaxError, ValueError):
            pass
    
    # If all parsing fails, return empty domain
    logger.warning(f"Failed to parse Odoo domain: {domain_str}")
    return []


def format_odoo_error(error: Exception) -> str:
    """Format Odoo errors for user-friendly display"""
    if isinstance(error, xmlrpc.client.Fault):
        # Extract the actual error message from Odoo's fault
        message = error.faultString
        
        # Try to clean up common Odoo error formats
        if "ValidationError" in message:
            # Extract the actual validation message
            import re
            match = re.search(r"ValidationError: (.*)", message)
            if match:
                return f"Validation Error: {match.group(1)}"
        
        return message
    
    return str(error)


def get_env_or_default(key: str, default: Any) -> Any:
    """Get environment variable or return default value"""
    value = os.getenv(key)
    if value is None:
        return default
    
    # Try to parse as JSON for complex types
    if isinstance(default, (dict, list, bool, int, float)):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # For booleans
            if isinstance(default, bool):
                return value.lower() in ('true', 'yes', '1', 'y')
            # For integers
            elif isinstance(default, int):
                try:
                    return int(value)
                except ValueError:
                    return default
            # For floats
            elif isinstance(default, float):
                try:
                    return float(value)
                except ValueError:
                    return default
    
    return value
