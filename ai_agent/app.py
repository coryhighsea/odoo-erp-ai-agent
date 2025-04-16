from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import os
from dotenv import load_dotenv
import xmlrpc.client
import json
import logging
from agents import MainAgent, SalesAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8069"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Odoo connection settings
ODOO_URL = os.getenv("ODOO_URL", "http://web:8069")
ODOO_DB = os.getenv("ODOO_DB", "HISEY")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "cjhisey@gmail.com")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "odoo")

# Anthropic settings
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# Initialize agents
main_agent = MainAgent(ANTHROPIC_API_KEY)
sales_agent = SalesAgent(ANTHROPIC_API_KEY)

class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None
    conversation_history: Optional[List[dict]] = None
    agent_type: str = "main"  # "main" or "sales"

class DatabaseOperation(BaseModel):
    model: str
    method: str
    args: List[Any]
    kwargs: Dict[str, Any] = {}

def connect_to_odoo():
    """Establish connection to Odoo instance"""
    try:
        logger.info(f"Connecting to Odoo at {ODOO_URL} with database {ODOO_DB}")
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        if not uid:
            raise Exception("Authentication failed. Please check your credentials and database name.")
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        logger.info("Successfully connected to Odoo")
        return uid, models
    except Exception as e:
        logger.error(f"Error connecting to Odoo: {str(e)}")
        raise

def execute_database_operation(operation: DatabaseOperation):
    """Execute a database operation safely"""
    try:
        logger.info(f"Executing database operation: {operation.model}.{operation.method}")
        logger.info(f"Args: {operation.args}")
        logger.info(f"Kwargs: {operation.kwargs}")
        
        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Execute the operation
        result = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            operation.model,
            operation.method,
            operation.args,
            operation.kwargs
        )
        
        logger.info(f"Operation successful. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error executing database operation: {str(e)}")
        raise

async def process_with_agents(message: str, agent_type: str = "main") -> str:
    """Process the message with the appropriate agent"""
    try:
        if agent_type == "main":
            response = await main_agent.process_message(message)
            
            # Check for delegation to sales agent
            if "DELEGATE_TO_SALES_AGENT:" in response:
                instruction_str = response.split("DELEGATE_TO_SALES_AGENT:")[1].strip()
                instruction = json.loads(instruction_str)
                sales_response = await sales_agent.process_instruction(instruction)
                return f"{response}\n\nSales Agent Response:\n{sales_response}"
            
            return response
            
        elif agent_type == "sales":
            instruction = json.loads(message)
            return await sales_agent.process_instruction(instruction)
            
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
    except Exception as e:
        logger.error(f"Error in agent processing: {str(e)}")
        return f"Error processing message: {str(e)}"

@app.get("/ping")
async def ping():
    """Test endpoint to verify service health"""
    try:
        # Test Odoo connection
        try:
            connect_to_odoo()
            odoo_connected = True
        except Exception as e:
            logger.error(f"Odoo connection failed: {str(e)}")
            odoo_connected = False
        
        return {
            "status": "ok",
            "odoo_connected": odoo_connected
        }
    except Exception as e:
        logger.error(f"Ping test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(message: ChatMessage):
    try:
        logger.info(f"Received chat message: {message.message}")
        logger.info(f"Agent type: {message.agent_type}")
        
        # Process the message with the appropriate agent
        response = await process_with_agents(message.message, message.agent_type)
        
        # Check if the response contains a database operation
        try:
            if "DATABASE_OPERATION:" in response:
                operation_str = response.split("DATABASE_OPERATION:")[1].strip()
                operation = DatabaseOperation(**json.loads(operation_str))
                result = execute_database_operation(operation)
                response = response.split("DATABASE_OPERATION:")[0] + f"\nOperation successful: {result}"
        except Exception as e:
            logger.error(f"Error processing database operation: {str(e)}")
            response = f"Error processing database operation: {str(e)}"
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 