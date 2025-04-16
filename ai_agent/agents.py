from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import anthropic
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentContext(BaseModel):
    """Shared context between agents"""
    conversation_history: List[Dict[str, str]]
    usage: Dict[str, int]
    customer_id: Optional[int] = None
    sales_agent_id: Optional[int] = None

class MainAgent:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.context = AgentContext(
            conversation_history=[],
            usage={"requests": 0, "tokens": 0}
        )

    async def process_message(self, message: str) -> str:
        """Process a message with the main agent"""
        try:
            # Update context
            self.context.conversation_history.append({
                "role": "user",
                "content": message
            })

            # Prepare system prompt
            system_prompt = self._get_system_prompt()

            # Call Claude
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2000,
                system=system_prompt,
                messages=self.context.conversation_history
            )

            # Update context
            self.context.conversation_history.append({
                "role": "assistant",
                "content": response.content[0].text
            })
            self.context.usage["requests"] += 1
            self.context.usage["tokens"] += response.usage.input_tokens + response.usage.output_tokens

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error in main agent: {str(e)}")
            return f"Error processing message: {str(e)}"

    def _get_system_prompt(self) -> str:
        return """You are the main AI assistant for an Odoo ERP system. You can:
        1. Answer questions about the system
        2. Make database operations
        3. Delegate tasks to the sales agent
        4. Coordinate between different system components

        When delegating to the sales agent, use the format:
        DELEGATE_TO_SALES_AGENT:{{"instruction": "your instruction here", "customer_id": 123}}

        When making database operations, use the format:
        DATABASE_OPERATION:{{"model": "model.name", "method": "method_name", "args": [...]}}"""

class SalesAgent:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.context = AgentContext(
            conversation_history=[],
            usage={"requests": 0, "tokens": 0}
        )

    async def process_instruction(self, instruction: Dict[str, Any]) -> str:
        """Process an instruction from the main agent"""
        try:
            # Update context
            self.context.conversation_history.append({
                "role": "user",
                "content": json.dumps(instruction)
            })

            # Prepare system prompt
            system_prompt = self._get_system_prompt()

            # Call Claude
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2000,
                system=system_prompt,
                messages=self.context.conversation_history
            )

            # Update context
            self.context.conversation_history.append({
                "role": "assistant",
                "content": response.content[0].text
            })
            self.context.usage["requests"] += 1
            self.context.usage["tokens"] += response.usage.input_tokens + response.usage.output_tokens

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error in sales agent: {str(e)}")
            return f"Error processing instruction: {str(e)}"

    def _get_system_prompt(self) -> str:
        return """You are a sales agent in an Odoo ERP system. You can:
        1. Send emails to customers
        2. Schedule follow-ups
        3. Manage customer communications
        4. Track customer interactions

        When sending emails, use the format:
        DATABASE_OPERATION:{{"model": "sales.agent", "method": "process_instruction", "args": [[1], {{"type": "email", "customer_id": 123, "template_name": "template_name", "subject": "subject", "body": "body"}}]}}

        When scheduling follow-ups, use the format:
        DATABASE_OPERATION:{{"model": "sales.agent", "method": "process_instruction", "args": [[1], {{"type": "follow_up", "customer_id": 123, "date": "2024-03-20", "notes": "notes"}}]}}""" 