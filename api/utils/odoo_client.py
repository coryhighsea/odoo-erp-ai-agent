"""
Odoo XML-RPC client utility for the Odoo ERP AI Agent API
"""
import xmlrpc.client
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union
import os
from functools import wraps
import json
import asyncio
from datetime import datetime

from ..models.odoo import OdooContext
from ..utils.helpers import timed_execution, format_odoo_error
from config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, ODOO_API_KEY, DEFAULT_TIMEOUT

# Configure logging
logger = logging.getLogger(__name__)


class OdooClient:
    """Client for interacting with Odoo via XML-RPC"""
    
    def __init__(self, url: Optional[str] = None, database: Optional[str] = None, 
                username: Optional[str] = None, password: Optional[str] = None,
                api_key: Optional[str] = None):
        """Initialize Odoo client with configuration"""
        self.url = url or ODOO_URL
        self.database = database or ODOO_DB
        self.username = username or ODOO_USERNAME
        self.password = password or ODOO_PASSWORD
        self.api_key = api_key or ODOO_API_KEY
        
        self.uid = None
        self.common_proxy = None
        self.models_proxy = None
        self.version_info = None
        self.last_error = None
        self.connected = False
    
    def connect(self) -> Tuple[bool, Union[int, None], str, Optional[Dict[str, Any]]]:
        """Connect to Odoo server and authenticate
        
        Returns:
            Tuple containing (success, uid, message, version_info)
        """
        try:
            logger.info(f"Connecting to Odoo at {self.url}")
            self.common_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            
            # Get version info
            self.version_info = self.common_proxy.version()
            
            # Authenticate
            self.uid = self.common_proxy.authenticate(
                self.database,
                self.username,
                self.password,
                {}
            )
            
            if not self.uid:
                logger.error("Authentication failed")
                self.last_error = "Authentication failed. Check credentials and database name."
                self.connected = False
                return False, None, self.last_error, self.version_info
            
            # Initialize models proxy
            self.models_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            
            logger.info(f"Successfully connected to Odoo with UID: {self.uid}")
            self.connected = True
            return True, self.uid, "Successfully connected to Odoo", self.version_info
            
        except xmlrpc.client.Fault as e:
            self.last_error = format_odoo_error(e)
            logger.error(f"XMLRPC Fault: {self.last_error}")
            self.connected = False
            return False, None, self.last_error, None
        except ConnectionRefusedError:
            self.last_error = "Connection refused. Check if Odoo server is running."
            logger.error(self.last_error)
            self.connected = False
            return False, None, self.last_error, None
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error connecting to Odoo: {self.last_error}")
            self.connected = False
            return False, None, f"Error: {self.last_error}", None
    
    @timed_execution
    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Execute a method on an Odoo model
        
        Args:
            model: Odoo model name
            method: Method to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of the method execution
        """
        if not self.uid or not self.models_proxy or not self.connected:
            success, uid, message, _ = self.connect()
            if not success:
                raise Exception(f"Not connected to Odoo: {message}")
        
        try:
            # Prepare args for execute_kw
            execute_args = [
                self.database,
                self.uid,
                self.password,
                model,
                method
            ]
            
            # Add method args and kwargs if provided
            if args:
                execute_args.append(args)
            if kwargs:
                execute_args.append(kwargs)
            
            # Execute the method
            return self.models_proxy.execute_kw(*execute_args)
            
        except xmlrpc.client.Fault as e:
            error_msg = format_odoo_error(e)
            logger.error(f"XMLRPC Fault: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error executing method: {str(e)}")
            raise Exception(f"Error: {str(e)}")
    
    def get_models(self, name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available models
        
        Args:
            name_filter: Optional filter for model names
            
        Returns:
            List of model information dictionaries
        """
        # Prepare domain
        domain = [('state', '=', 'base')]
        if name_filter:
            domain.append(('model', 'ilike', name_filter))
        
        # Get model IDs
        model_ids = self.execute("ir.model", "search", domain)
        
        # Get model details
        fields_to_read = ['name', 'model', 'description', 'transient']
        models = self.execute("ir.model", "read", model_ids, fields_to_read)
        
        return models
    
    def get_model_fields(self, model_name: str) -> Dict[str, Dict[str, Any]]:
        """Get fields information for a model
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary of field information
        """
        fields_info = self.execute(model_name, "fields_get")
        return fields_info
    
    def search_read(self, model: str, domain: List, fields: Optional[List[str]] = None, 
                   limit: Optional[int] = None, offset: Optional[int] = 0,
                   order: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search and read records from a model
        
        Args:
            model: Model name
            domain: Search domain
            fields: Fields to include in the result
            limit: Maximum number of records
            offset: Offset for pagination
            order: Sort order
            
        Returns:
            List of records
        """
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
        if limit:
            kwargs["limit"] = limit
        if offset:
            kwargs["offset"] = offset
        if order:
            kwargs["order"] = order
        
        return self.execute(model, "search_read", domain, **kwargs)
    
    def create(self, model: str, values: Dict[str, Any]) -> int:
        """Create a new record
        
        Args:
            model: Model name
            values: Field values
            
        Returns:
            ID of the created record
        """
        return self.execute(model, "create", values)
    
    def write(self, model: str, ids: List[int], values: Dict[str, Any]) -> bool:
        """Update existing records
        
        Args:
            model: Model name
            ids: Record IDs
            values: Field values to update
            
        Returns:
            True if successful
        """
        return self.execute(model, "write", ids, values)
    
    def unlink(self, model: str, ids: List[int]) -> bool:
        """Delete records
        
        Args:
            model: Model name
            ids: Record IDs
            
        Returns:
            True if successful
        """
        return self.execute(model, "unlink", ids)
    
    def get_record_name(self, model: str, record_id: int) -> str:
        """Get the display name of a record
        
        Args:
            model: Model name
            record_id: Record ID
            
        Returns:
            Display name of the record
        """
        result = self.execute(model, "name_get", [record_id])
        if result and result[0]:
            return result[0][1]
        return ""
    
    def check_access_rights(self, model: str, operation: str) -> bool:
        """Check if the user has access rights for an operation
        
        Args:
            model: Model name
            operation: Operation (read, write, create, unlink)
            
        Returns:
            True if the user has access rights
        """
        try:
            return self.execute(model, "check_access_rights", operation, False)
        except Exception:
            return False
    
    async def execute_async(self, model: str, method: str, *args, **kwargs) -> Tuple[Any, int]:
        """Execute a method asynchronously
        
        Args:
            model: Odoo model name
            method: Method to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Tuple of (result, execution_time_ms)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.execute(model, method, *args, **kwargs)
        )
