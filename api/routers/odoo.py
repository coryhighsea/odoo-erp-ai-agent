from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional, Union
import time
import uuid
from datetime import datetime
import asyncio
import logging
import xmlrpc.client

from api.models.requests import OdooConnectionRequest, OdooExecuteRequest, OdooMethodType, PaginationRequest
from api.models.responses import (
    OdooConnectionResponse, OdooModel, OdooModelsResponse, 
    OdooExecuteResponse, ErrorResponse
)
from api.models.odoo import OdooModelSchema, OdooRecord, OdooBatchResult
from api.middleware.auth import verify_api_key, rate_limit
from api.utils.helpers import (
    generate_trace_id, format_error_response, create_paginated_response,
    timed_execution, format_odoo_error
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/odoo", tags=["Odoo"])


class OdooClient:
    """Simple Odoo XML-RPC client"""
    
    def __init__(self, url: str, database: str, username: str, password: str):
        self.url = url
        self.database = database
        self.username = username
        self.password = password
        self.uid = None
        self.common_proxy = None
        self.models_proxy = None
    
    def connect(self):
        """Connect to Odoo and authenticate"""
        try:
            self.common_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            version_info = self.common_proxy.version()
            
            self.uid = self.common_proxy.authenticate(
                self.database, self.username, self.password, {}
            )
            
            if not self.uid:
                return False, None, "Authentication failed", version_info
            
            self.models_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            return True, self.uid, "Successfully connected", version_info
        except Exception as e:
            return False, None, format_odoo_error(e), None
    
    @timed_execution
    def execute(self, model, method, *args, **kwargs):
        """Execute a method on an Odoo model"""
        if not self.uid or not self.models_proxy:
            success, uid, message, _ = self.connect()
            if not success:
                raise Exception(message)
        
        try:
            return self.models_proxy.execute_kw(
                self.database, self.uid, self.password,
                model, method, args, kwargs
            )
        except Exception as e:
            raise Exception(format_odoo_error(e))


@router.post("/connect", response_model=OdooConnectionResponse, status_code=200, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def connect_to_odoo(
    config: OdooConnectionRequest,
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Test or establish a connection to an Odoo instance
    
    This endpoint attempts to connect to an Odoo instance with the provided
    credentials and returns the connection status.
    """
    try:
        # Create Odoo client with provided config
        client = OdooClient(
            url=str(config.url),
            database=config.database,
            username=config.username,
            password=config.password
        )
        
        # Attempt to connect
        success, uid, message, version_info = client.connect()
        
        # Get version info if available
        version = None
        if version_info:
            version = version_info.get('server_version', None)
        
        # Return connection response
        return OdooConnectionResponse(
            success=success,
            uid=uid,
            version=version,
            message=message,
            details={
                "server_info": version_info,
                "timestamp": datetime.now().isoformat()
            } if success else None
        )
    except Exception as e:
        logger.error(f"Error connecting to Odoo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Connection Error", 
                str(e)
            )
        )


@router.get("/models", response_model=OdooModelsResponse, status_code=200, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def list_odoo_models(
    filter: Optional[str] = Query(None, description="Filter models by name"),
    include_fields: bool = Query(False, description="Include model fields information"),
    pagination: PaginationRequest = Depends(),
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    List available Odoo models
    
    This endpoint returns a paginated list of available models in the Odoo instance.
    Optionally filter models by name and include field information.
    """
    try:
        # Create Odoo client
        # In a real implementation, this would use connection details from environment or database
        client = OdooClient(
            url="http://localhost:8069",  # Placeholder - replace with actual config
            database="odoo",
            username="admin",
            password="admin"
        )
        
        # Connect to Odoo
        success, uid, message, _ = client.connect()
        if not success:
            raise Exception(f"Failed to connect to Odoo: {message}")
        
        # Search for models
        domain = []
        if filter:
            domain = [('model', 'ilike', filter)]
        
        # Get model IDs
        model_ids = client.execute("ir.model", "search", domain)[0]
        
        # Get total count for pagination
        total_count = len(model_ids)
        
        # Apply pagination
        paginated_ids = model_ids[
            (pagination.page - 1) * pagination.page_size:
            pagination.page * pagination.page_size
        ]
        
        # Get model details
        fields_to_read = ['name', 'model', 'description', 'transient']
        models_data = client.execute("ir.model", "read", paginated_ids, fields_to_read)[0]
        
        # Create model objects
        models = []
        for model_data in models_data:
            # Get fields if requested
            fields = None
            if include_fields:
                try:
                    fields = client.execute(model_data['model'], "fields_get")[0]
                except Exception:
                    # Skip fields if error occurs
                    pass
            
            models.append(OdooModel(
                name=model_data['model'],
                description=model_data.get('description', None),
                transient=model_data.get('transient', False),
                fields=fields
            ))
        
        # Return response
        return OdooModelsResponse(
            models=models,
            count=total_count,
            filter_applied=filter
        )
    except Exception as e:
        logger.error(f"Error listing Odoo models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Models Listing Error", 
                str(e)
            )
        )


@router.post("/execute", response_model=OdooExecuteResponse, status_code=200, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def execute_odoo_operation(
    request: OdooExecuteRequest,
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Execute a specific operation on an Odoo model
    
    This endpoint executes a method on an Odoo model with the provided arguments.
    """
    try:
        # Create Odoo client
        # In a real implementation, this would use connection details from environment or database
        client = OdooClient(
            url="http://localhost:8069",  # Placeholder - replace with actual config
            database="odoo",
            username="admin",
            password="admin"
        )
        
        # Connect to Odoo
        success, uid, message, _ = client.connect()
        if not success:
            raise Exception(f"Failed to connect to Odoo: {message}")
        
        # Determine method to execute
        method = request.custom_method if request.method == OdooMethodType.CUSTOM else request.method
        
        # Execute method
        result, execution_time_ms = client.execute(
            request.model,
            method,
            *request.args,
            **request.kwargs
        )
        
        # Return response
        return OdooExecuteResponse(
            success=True,
            result=result,
            execution_time_ms=execution_time_ms
        )
    except Exception as e:
        logger.error(f"Error executing Odoo operation: {str(e)}", exc_info=True)
        return OdooExecuteResponse(
            success=False,
            error=str(e),
            execution_time_ms=0
        )


@router.get("/schema/{model_name}", status_code=200, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def get_model_schema(
    model_name: str = Path(..., description="Odoo model name"),
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Get the schema for a specific Odoo model
    
    This endpoint returns detailed field information for a specific Odoo model.
    """
    try:
        # Create Odoo client
        client = OdooClient(
            url="http://localhost:8069",  # Placeholder - replace with actual config
            database="odoo",
            username="admin",
            password="admin"
        )
        
        # Connect to Odoo
        success, uid, message, _ = client.connect()
        if not success:
            raise Exception(f"Failed to connect to Odoo: {message}")
        
        # Check if model exists
        model_ids = client.execute("ir.model", "search", [
            ['model', '=', model_name]
        ])[0]
        
        if not model_ids:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    404, 
                    "Not Found", 
                    f"Model '{model_name}' not found"
                )
            )
        
        # Get model fields
        fields = client.execute(model_name, "fields_get")[0]
        
        # Get model info
        model_info = client.execute("ir.model", "read", model_ids, [
            'name', 'model', 'description', 'transient'
        ])[0][0]
        
        # Return schema
        return {
            "model": model_name,
            "description": model_info.get('description', ''),
            "transient": model_info.get('transient', False),
            "fields": fields
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model schema: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Schema Retrieval Error", 
                str(e)
            )
        )


@router.post("/batch", status_code=200, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def execute_batch_operations(
    requests: List[OdooExecuteRequest],
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Execute multiple Odoo operations in a batch
    
    This endpoint executes multiple operations on Odoo models in a single request.
    """
    try:
        # Create Odoo client
        client = OdooClient(
            url="http://localhost:8069",  # Placeholder - replace with actual config
            database="odoo",
            username="admin",
            password="admin"
        )
        
        # Connect to Odoo
        success, uid, message, _ = client.connect()
        if not success:
            raise Exception(f"Failed to connect to Odoo: {message}")
        
        # Execute each request
        results = []
        for i, request in enumerate(requests):
            try:
                # Determine method to execute
                method = request.custom_method if request.method == OdooMethodType.CUSTOM else request.method
                
                # Execute method
                result, execution_time_ms = client.execute(
                    request.model,
                    method,
                    *request.args,
                    **request.kwargs
                )
                
                # Add to results
                results.append(OdooBatchResult(
                    index=i,
                    success=True,
                    result=result,
                    error=None,
                    execution_time_ms=execution_time_ms
                ))
            except Exception as e:
                # Add error to results
                results.append(OdooBatchResult(
                    index=i,
                    success=False,
                    result=None,
                    error=str(e),
                    execution_time_ms=0
                ))
        
        # Return batch results
        return {
            "batch_size": len(requests),
            "success_count": sum(1 for r in results if r.success),
            "error_count": sum(1 for r in results if not r.success),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error executing batch operations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Batch Execution Error", 
                str(e)
            )
        )


@router.get("/records/{model_name}", status_code=200, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def get_model_records(
    model_name: str = Path(..., description="Odoo model name"),
    domain: Optional[str] = Query("[]", description="Search domain as JSON array"),
    fields: Optional[str] = Query(None, description="Fields to include, comma-separated"),
    limit: Optional[int] = Query(100, description="Maximum number of records to return"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
    order: Optional[str] = Query(None, description="Sort order, e.g., 'name ASC, id DESC'"),
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Get records for a specific Odoo model
    
    This endpoint returns records for a specific Odoo model based on the provided search criteria.
    """
    try:
        # Create Odoo client
        client = OdooClient(
            url="http://localhost:8069",  # Placeholder - replace with actual config
            database="odoo",
            username="admin",
            password="admin"
        )
        
        # Connect to Odoo
        success, uid, message, _ = client.connect()
        if not success:
            raise Exception(f"Failed to connect to Odoo: {message}")
        
        # Parse domain
        try:
            import json
            search_domain = json.loads(domain)
        except json.JSONDecodeError:
            search_domain = []
        
        # Parse fields
        field_list = None
        if fields:
            field_list = [f.strip() for f in fields.split(",") if f.strip()]
        
        # Check if model exists
        model_ids = client.execute("ir.model", "search", [
            ['model', '=', model_name]
        ])[0]
        
        if not model_ids:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    404, 
                    "Not Found", 
                    f"Model '{model_name}' not found"
                )
            )
        
        # Get record count
        count = client.execute(model_name, "search_count", search_domain)[0]
        
        # Get records
        kwargs = {}
        if field_list:
            kwargs["fields"] = field_list
        if limit:
            kwargs["limit"] = limit
        if offset:
            kwargs["offset"] = offset
        if order:
            kwargs["order"] = order
        
        records = client.execute(model_name, "search_read", search_domain, **kwargs)[0]
        
        # Return records
        return {
            "model": model_name,
            "total_count": count,
            "limit": limit,
            "offset": offset,
            "records": records
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model records: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Records Retrieval Error", 
                str(e)
            )
        )
