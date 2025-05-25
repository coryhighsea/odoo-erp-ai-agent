from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Generic, TypeVar
from datetime import datetime
from enum import Enum
import uuid
from pydantic.json import timedelta_isoformat


class ErrorResponse(BaseModel):
    """Standard error response model"""
    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})
    
    status_code: int = Field(..., description="HTTP status code")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique trace ID for error tracking")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})
    
    status: HealthStatus = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    components: Dict[str, HealthStatus] = Field(..., description="Status of individual components")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")


T = TypeVar('T')


class PaginatedResponse(Generic[T]):
    """Base model for paginated responses"""
    items: List[T] = Field(..., description="List of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Model for a single message in a conversation"""
    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})
    
    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message ID")


class AgentResponse(BaseModel):
    """Response model for agent queries"""
    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})
    
    response: str = Field(..., description="Agent response message")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    created_at: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Trace ID for request tracking")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    source_references: Optional[List[Dict[str, Any]]] = Field(None, description="References to information sources")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score for the response")


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXPIRED = "expired"


class SessionInfo(BaseModel):
    """Model for session information"""
    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})
    
    session_id: str = Field(..., description="Unique session ID")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last session update timestamp")
    status: SessionStatus = Field(..., description="Current session status")
    message_count: int = Field(..., description="Number of messages in the session")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")


class SessionHistoryResponse(BaseModel):
    """Model for session history response"""
    session_id: str = Field(..., description="Session ID")
    messages: List[Message] = Field(..., description="List of messages in the session")
    session_info: SessionInfo = Field(..., description="Session information")


class OdooConnectionResponse(BaseModel):
    """Response model for Odoo connection tests"""
    success: bool = Field(..., description="Whether the connection was successful")
    uid: Optional[int] = Field(None, description="User ID if connection successful")
    version: Optional[str] = Field(None, description="Odoo version if available")
    message: str = Field(..., description="Connection status message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional connection details")


class OdooModel(BaseModel):
    """Model for Odoo model information"""
    name: str = Field(..., description="Model technical name")
    description: Optional[str] = Field(None, description="Model description")
    transient: bool = Field(False, description="Whether the model is transient")
    fields: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Model fields information")


class OdooModelsResponse(BaseModel):
    """Response model for Odoo models listing"""
    models: List[OdooModel] = Field(..., description="List of available Odoo models")
    count: int = Field(..., description="Total number of models")
    filter_applied: Optional[str] = Field(None, description="Filter applied to the models list")


class OdooExecuteResponse(BaseModel):
    """Response model for Odoo execute operations"""
    success: bool = Field(..., description="Whether the operation was successful")
    result: Any = Field(None, description="Operation result")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")


class WebhookResponse(BaseModel):
    """Response model for webhook operations"""
    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})
    
    success: bool = Field(..., description="Whether the webhook operation was successful")
    webhook_id: str = Field(..., description="Webhook ID")
    message: str = Field(..., description="Operation message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Operation timestamp")
