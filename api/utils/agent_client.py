"""
AI Agent client utility for the Odoo ERP AI Agent API
"""
import requests
import logging
import time
import json
import os
from typing import Dict, List, Any, Optional, Union, Tuple
import uuid
from datetime import datetime
import asyncio
import httpx

from ..models.responses import Message, MessageRole, AgentResponse
from ..models.requests import AgentQueryRequest
from ..utils.helpers import timed_execution_async, generate_trace_id
from config import AI_AGENT_URL, DEFAULT_TIMEOUT, LONG_TIMEOUT

# Configure logging
logger = logging.getLogger(__name__)


class AgentClient:
    """Client for interacting with the Odoo AI Agent"""
    
    def __init__(self, agent_url: Optional[str] = None):
        """Initialize Agent client"""
        self.agent_url = agent_url or AI_AGENT_URL
        self.session_store: Dict[str, List[Message]] = {}
        self.client = httpx.AsyncClient(timeout=LONG_TIMEOUT)
    
    async def query_agent(self, request: AgentQueryRequest) -> Tuple[AgentResponse, int]:
        """Send a query to the AI agent
        
        Args:
            request: The agent query request
            
        Returns:
            Tuple of (agent response, processing time in ms)
        """
        start_time = time.time()
        session_id = request.session_id or str(uuid.uuid4())
        trace_id = request.trace_id or generate_trace_id()
        
        try:
            # Prepare conversation history if needed
            conversation_history = None
            if request.include_history and session_id in self.session_store:
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in self.session_store[session_id]
                ]
            
            # Prepare request payload
            payload = {
                "message": request.message,
                "context": request.context or {},
                "conversation_history": conversation_history
            }
            
            logger.info(f"Sending query to agent with trace_id: {trace_id}")
            
            # Send request to agent
            response = await self.client.post(
                f"{self.agent_url}/chat",
                json=payload,
                headers={"X-Trace-Id": trace_id}
            )
            
            if response.status_code != 200:
                logger.error(f"Agent error: {response.status_code} - {response.text}")
                raise Exception(f"Agent error: {response.status_code} - {response.text}")
            
            # Parse response
            response_data = response.json()
            agent_response = response_data.get("response", "")
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Store messages in session history
            if session_id not in self.session_store:
                self.session_store[session_id] = []
                
                # Add initial system message for new sessions
                self.session_store[session_id].append(
                    Message(
                        role=MessageRole.SYSTEM,
                        content="I am an AI assistant for Odoo ERP. How can I help you today?",
                        timestamp=datetime.now(),
                        message_id=str(uuid.uuid4())
                    )
                )
            
            # Add user message to history
            self.session_store[session_id].append(
                Message(
                    role=MessageRole.USER,
                    content=request.message,
                    timestamp=datetime.now(),
                    message_id=str(uuid.uuid4())
                )
            )
            
            # Add assistant response to history
            self.session_store[session_id].append(
                Message(
                    role=MessageRole.ASSISTANT,
                    content=agent_response,
                    timestamp=datetime.now(),
                    message_id=str(uuid.uuid4())
                )
            )
            
            # Create response object
            agent_response_obj = AgentResponse(
                response=agent_response,
                session_id=session_id,
                created_at=datetime.now(),
                trace_id=trace_id,
                processing_time_ms=processing_time_ms,
                source_references=response_data.get("source_references"),
                metadata=response_data.get("metadata"),
                confidence_score=response_data.get("confidence_score", 0.95)
            )
            
            return agent_response_obj, processing_time_ms
            
        except httpx.RequestError as e:
            logger.error(f"Could not connect to AI agent service: {str(e)}")
            raise Exception(f"Could not connect to AI agent service: {str(e)}")
        except Exception as e:
            logger.error(f"Error querying agent: {str(e)}")
            raise Exception(f"Error: {str(e)}")
    
    def get_session_history(self, session_id: str) -> List[Message]:
        """Get conversation history for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of messages in the session
        """
        if session_id not in self.session_store:
            return []
        
        return self.session_store[session_id]
    
    async def create_session(self, initial_message: Optional[str] = None, 
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new conversation session
        
        Args:
            initial_message: Optional initial message
            metadata: Optional session metadata
            
        Returns:
            New session ID
        """
        session_id = str(uuid.uuid4())
        self.session_store[session_id] = []
        
        # Add initial system message
        self.session_store[session_id].append(
            Message(
                role=MessageRole.SYSTEM,
                content="I am an AI assistant for Odoo ERP. How can I help you today?",
                timestamp=datetime.now(),
                message_id=str(uuid.uuid4())
            )
        )
        
        # Add initial user message and get response if provided
        if initial_message:
            request = AgentQueryRequest(
                message=initial_message,
                session_id=session_id,
                include_history=True
            )
            
            try:
                await self.query_agent(request)
            except Exception as e:
                logger.error(f"Error processing initial message: {str(e)}")
                # Still create the session even if initial message fails
                self.session_store[session_id].append(
                    Message(
                        role=MessageRole.USER,
                        content=initial_message,
                        timestamp=datetime.now(),
                        message_id=str(uuid.uuid4())
                    )
                )
        
        return session_id
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if session was deleted, False if it didn't exist
        """
        if session_id in self.session_store:
            del self.session_store[session_id]
            return True
        return False
    
    async def check_agent_health(self) -> Tuple[bool, str, int]:
        """Check if the agent is healthy
        
        Returns:
            Tuple of (is_healthy, message, latency_ms)
        """
        start_time = time.time()
        
        try:
            # Try to connect to agent ping endpoint
            response = await self.client.get(f"{self.agent_url}/ping", timeout=DEFAULT_TIMEOUT)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                return True, "Agent is healthy", latency_ms
            else:
                return False, f"Agent returned status code: {response.status_code}", latency_ms
                
        except httpx.RequestError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return False, f"Could not connect to agent: {str(e)}", latency_ms
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return False, f"Error checking agent health: {str(e)}", latency_ms
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
