from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import time
import uuid
from datetime import datetime
import asyncio
import logging

# In-memory session store (this would be replaced with a database in production)
session_store = {}

from api.models.requests import AgentQueryRequest, SessionCreateRequest, SessionUpdateRequest, PaginationRequest
from api.models.responses import (
    AgentResponse, SessionInfo, SessionStatus, SessionHistoryResponse, 
    Message, MessageRole, ErrorResponse
)
from api.middleware.auth import verify_api_key, rate_limit
from api.utils.helpers import generate_trace_id, format_error_response, create_paginated_response

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/agent", tags=["Agent"])

# In-memory session store (replace with database in production)
session_store: Dict[str, List[Message]] = {}


@router.post("/query", response_model=AgentResponse, status_code=200, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def query_agent(
    request: AgentQueryRequest,
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Send a query to the Odoo AI agent
    
    This endpoint processes a user query and returns the AI agent's response.
    If a session_id is provided, the conversation history will be maintained.
    """
    try:
        # Generate trace ID if not provided
        trace_id = request.trace_id or generate_trace_id()
        
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Prepare conversation history if needed
        conversation_history = None
        if request.include_history and session_id in session_store:
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in session_store[session_id]
            ]
        
        # Prepare request payload
        payload = {
            "message": request.message,
            "context": request.context or {},
            "conversation_history": conversation_history
        }
        
        logger.info(f"Sending query to agent with trace_id: {trace_id}")
        
        # TODO: Replace with actual agent client implementation
        # This is a placeholder for demonstration
        await asyncio.sleep(1)  # Simulate processing time
        agent_response = f"This is a simulated response to: {request.message}"
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Store messages in session history
        if session_id not in session_store:
            session_store[session_id] = []
            
            # Add initial system message for new sessions
            session_store[session_id].append(
                Message(
                    role=MessageRole.SYSTEM,
                    content="I am an AI assistant for Odoo ERP. How can I help you today?",
                    timestamp=datetime.now(),
                    message_id=str(uuid.uuid4())
                )
            )
        
        # Add user message to history
        session_store[session_id].append(
            Message(
                role=MessageRole.USER,
                content=request.message,
                timestamp=datetime.now(),
                message_id=str(uuid.uuid4())
            )
        )
        
        # Add assistant response to history
        session_store[session_id].append(
            Message(
                role=MessageRole.ASSISTANT,
                content=agent_response,
                timestamp=datetime.now(),
                message_id=str(uuid.uuid4())
            )
        )
        
        # Create response object
        return AgentResponse(
            response=agent_response,
            session_id=session_id,
            created_at=datetime.now(),
            trace_id=trace_id,
            processing_time_ms=processing_time_ms,
            source_references=None,
            metadata={
                "query_length": len(request.message),
                "response_length": len(agent_response)
            },
            confidence_score=0.95  # Placeholder confidence score
        )
    except Exception as e:
        logger.error(f"Error in agent query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Agent Error", 
                str(e),
                {"trace_id": request.trace_id or generate_trace_id()}
            )
        )


@router.get("/status", status_code=200, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def get_agent_status(
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Check the status and health of the AI agent
    
    This endpoint verifies that the AI agent is operational and returns
    its current status information.
    """
    try:
        # Simple ping to check if agent is reachable
        start_time = time.time()
        
        # TODO: Replace with actual agent status check
        # This is a placeholder for demonstration
        await asyncio.sleep(0.1)  # Simulate status check
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "latency_ms": int((time.time() - start_time) * 1000),
            "version": "1.0.0",
            "sessions_count": len(session_store),
            "uptime": "1d 2h 34m",  # Placeholder uptime
            "load": {
                "requests_per_minute": 42,  # Placeholder metrics
                "average_response_time_ms": 250
            }
        }
    except Exception as e:
        logger.error(f"Error in agent status check: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Status Check Failed", 
                str(e)
            )
        )


@router.post("/sessions", response_model=SessionInfo, status_code=201, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def create_session(
    request: SessionCreateRequest,
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Create a new conversation session
    
    This endpoint creates a new session for maintaining conversation context
    between the user and the AI agent.
    """
    try:
        # Create a new session ID
        session_id = str(uuid.uuid4())
        
        # Initialize session with system message
        session_store[session_id] = [
            Message(
                role=MessageRole.SYSTEM,
                content="I am an AI assistant for Odoo ERP. How can I help you today?",
                timestamp=datetime.now(),
                message_id=str(uuid.uuid4())
            )
        ]
        
        # Add initial user message if provided
        if request.initial_message:
            session_store[session_id].append(
                Message(
                    role=MessageRole.USER,
                    content=request.initial_message,
                    timestamp=datetime.now(),
                    message_id=str(uuid.uuid4())
                )
            )
            
            # TODO: Process initial message with agent and add response
            # This is a placeholder for demonstration
            agent_response = f"This is a simulated response to: {request.initial_message}"
            
            session_store[session_id].append(
                Message(
                    role=MessageRole.ASSISTANT,
                    content=agent_response,
                    timestamp=datetime.now(),
                    message_id=str(uuid.uuid4())
                )
            )
        
        # Return session info
        return SessionInfo(
            session_id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=SessionStatus.ACTIVE,
            message_count=len(session_store[session_id]),
            metadata=request.metadata or {}
        )
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Session Creation Failed", 
                str(e)
            )
        )


@router.get("/sessions", status_code=200, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def list_sessions(
    pagination: PaginationRequest = Depends(),
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    List all available conversation sessions
    
    This endpoint returns a paginated list of all conversation sessions.
    """
    try:
        # Get all session IDs
        session_ids = list(session_store.keys())
        
        # Apply pagination
        total_items = len(session_ids)
        start_idx = (pagination.page - 1) * pagination.page_size
        end_idx = start_idx + pagination.page_size
        paginated_ids = session_ids[start_idx:end_idx]
        
        # Create session info objects
        sessions = []
        for session_id in paginated_ids:
            messages = session_store[session_id]
            sessions.append(SessionInfo(
                session_id=session_id,
                created_at=messages[0].timestamp if messages else datetime.now(),
                updated_at=messages[-1].timestamp if messages else datetime.now(),
                status=SessionStatus.ACTIVE,
                message_count=len(messages),
                metadata={}
            ))
        
        # Return paginated response
        return create_paginated_response(
            items=sessions,
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items
        )
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Session Listing Failed", 
                str(e)
            )
        )


@router.get("/sessions/{session_id}", response_model=SessionInfo, status_code=200, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def get_session(
    session_id: str = Path(..., description="Session ID"),
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Get information about a specific session
    
    This endpoint returns detailed information about a specific conversation session.
    """
    try:
        # Check if session exists
        if session_id not in session_store:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    404, 
                    "Not Found", 
                    f"Session with ID {session_id} not found"
                )
            )
        
        # Get session messages
        messages = session_store[session_id]
        
        # Return session info
        return SessionInfo(
            session_id=session_id,
            created_at=messages[0].timestamp if messages else datetime.now(),
            updated_at=messages[-1].timestamp if messages else datetime.now(),
            status=SessionStatus.ACTIVE,
            message_count=len(messages),
            metadata={}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Session Retrieval Failed", 
                str(e)
            )
        )


@router.put("/sessions/{session_id}", response_model=SessionInfo, status_code=200, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def update_session(
    request: SessionUpdateRequest,
    session_id: str = Path(..., description="Session ID"),
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Update a conversation session
    
    This endpoint updates the status or metadata of a specific conversation session.
    """
    try:
        # Check if session exists
        if session_id not in session_store:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    404, 
                    "Not Found", 
                    f"Session with ID {session_id} not found"
                )
            )
        
        # Get session messages
        messages = session_store[session_id]
        
        # Return updated session info
        return SessionInfo(
            session_id=session_id,
            created_at=messages[0].timestamp if messages else datetime.now(),
            updated_at=datetime.now(),
            status=SessionStatus(request.status) if request.status else SessionStatus.ACTIVE,
            message_count=len(messages),
            metadata=request.metadata or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Session Update Failed", 
                str(e)
            )
        )


@router.delete("/sessions/{session_id}", status_code=204, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def delete_session(
    session_id: str = Path(..., description="Session ID"),
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Delete a conversation session
    
    This endpoint deletes a specific conversation session and its history.
    """
    try:
        # Check if session exists
        if session_id not in session_store:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    404, 
                    "Not Found", 
                    f"Session with ID {session_id} not found"
                )
            )
        
        # Delete the session
        del session_store[session_id]
        
        # Return no content (204)
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "Session Deletion Failed", 
                str(e)
            )
        )


@router.get("/history/{session_id}", response_model=SessionHistoryResponse, status_code=200, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def get_session_history(
    session_id: str = Path(..., description="Session ID"),
    api_key: str = Depends(verify_api_key),
    _: None = Depends(rate_limit)
):
    """
    Get conversation history for a session
    
    This endpoint returns the complete conversation history for a specific session.
    """
    try:
        # Check if session exists
        if session_id not in session_store:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    404, 
                    "Not Found", 
                    f"Session with ID {session_id} not found"
                )
            )
        
        # Get session messages
        messages = session_store[session_id]
        
        # Get session info
        session_info = SessionInfo(
            session_id=session_id,
            created_at=messages[0].timestamp if messages else datetime.now(),
            updated_at=messages[-1].timestamp if messages else datetime.now(),
            status=SessionStatus.ACTIVE,
            message_count=len(messages),
            metadata={}
        )
        
        # Return session history
        return SessionHistoryResponse(
            session_id=session_id,
            messages=messages,
            session_info=session_info
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                500, 
                "History Retrieval Failed", 
                str(e)
            )
        )
