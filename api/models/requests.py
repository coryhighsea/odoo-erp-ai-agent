from pydantic import BaseModel, Field, validator, AnyHttpUrl
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import uuid


class PaginationRequest(BaseModel):
    """Pagination parameters for list endpoints"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @validator('page_size')
    def validate_page_size(cls, v):
        if v > 100:
            return 100
        return v


class AgentQueryRequest(BaseModel):
    """Request model for agent queries"""
    message: str = Field(..., description="User message to the AI agent")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the agent")
    include_history: bool = Field(True, description="Whether to include conversation history")
    trace_id: Optional[str] = Field(None, description="Trace ID for request tracking")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class SessionCreateRequest(BaseModel):
    """Model for creating a new session"""
    initial_message: Optional[str] = Field(None, description="Initial message to start the session")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")


class SessionUpdateRequest(BaseModel):
    """Model for updating a session"""
    status: Optional[str] = Field(None, description="New session status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated session metadata")


class OdooConnectionRequest(BaseModel):
    """Model for Odoo connection configuration"""
    url: AnyHttpUrl = Field(..., description="http://localhost:8069")
    database: str = Field(..., description="HISEY")
    username: str = Field(..., description="cjhisey@gmail.com")
    password: str = Field(..., description="odoo")
    api_key: Optional[str] = Field(None, description="Optional API key for authentication")
    
    @validator('database', 'username')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class OdooMethodType(str, Enum):
    """Enum for Odoo method types"""
    SEARCH = "search"
    SEARCH_READ = "search_read"
    READ = "read"
    CREATE = "create"
    WRITE = "write"
    UNLINK = "unlink"
    CUSTOM = "custom"


class OdooExecuteRequest(BaseModel):
    """Request model for executing Odoo operations"""
    model: str = Field(..., description="Odoo model name")
    method: OdooMethodType = Field(..., description="Method to execute")
    custom_method: Optional[str] = Field(None, description="Custom method name if method is CUSTOM")
    args: List[Any] = Field(default_factory=list, description="Positional arguments")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Keyword arguments")
    
    @validator('custom_method')
    def validate_custom_method(cls, v, values):
        if values.get('method') == OdooMethodType.CUSTOM and (not v or not v.strip()):
            raise ValueError("Custom method name is required when method is 'custom'")
        return v


class WebhookRequest(BaseModel):
    """Request model for webhook events"""
    event_type: str = Field(..., description="Type of webhook event")
    payload: Dict[str, Any] = Field(..., description="Webhook payload")
    timestamp: Optional[str] = Field(None, description="Event timestamp")
