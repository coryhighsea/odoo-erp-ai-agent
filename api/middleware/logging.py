from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid
import logging
import json
import os
from typing import Callable, Dict, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log details"""
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Log request details
        await self._log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.6f}"
            
            # Log response details
            self._log_response(response, request_id, process_time)
            
            return response
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request_id} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "process_time": f"{process_time:.6f}",
                    "exception": str(e),
                    "path": request.url.path,
                    "method": request.method
                }
            )
            raise
    
    async def _log_request(self, request: Request, request_id: str) -> None:
        """Log request details"""
        # Get client IP
        client_host = request.client.host if request.client else "unknown"
        
        # Get request body for specific content types
        body = ""
        if request.headers.get("Content-Type") in ["application/json", "application/x-www-form-urlencoded"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = body_bytes.decode()
                    # Truncate if too long
                    if len(body) > 1000:
                        body = body[:1000] + "... [truncated]"
            except Exception:
                body = "[Error reading body]"
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "client_ip": client_host,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "headers": dict(request.headers),
                "body": body,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _log_response(self, response: Response, request_id: str, process_time: float) -> None:
        """Log response details"""
        logger.info(
            f"Response: {response.status_code} - {process_time:.6f}s",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": f"{process_time:.6f}",
                "headers": dict(response.headers),
                "timestamp": datetime.now().isoformat()
            }
        )


class JSONLogFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "path": record.pathname,
            "line": record.lineno
        }
        
        # Add extra fields if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
            
        # Add all extra attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "exc_info", "exc_text", "stack_info", "lineno", 
                          "funcName", "created", "msecs", "relativeCreated", "levelname", 
                          "levelno", "pathname", "filename", "module", "name", "thread", 
                          "threadName", "processName", "process", "message", "msg"]:
                try:
                    # Try to serialize to JSON
                    json.dumps({key: value})
                    log_data[key] = value
                except (TypeError, OverflowError):
                    # If not JSON serializable, convert to string
                    log_data[key] = str(value)
        
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data)


def setup_logging():
    """Configure logging for the application"""
    # Get log level from environment
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Use JSON formatter if enabled
    use_json_logs = os.getenv("JSON_LOGS", "false").lower() == "true"
    if use_json_logs:
        console_handler.setFormatter(JSONLogFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Log configuration
    logger.info(f"Logging configured with level: {log_level_name}")
    
    return root_logger
