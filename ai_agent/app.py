from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.providers.anthropic import AnthropicProvider
from typing import List, Optional, Any, Dict, Tuple
import os
from dotenv import load_dotenv
import xmlrpc.client
import anthropic
import logging
import json
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8069", "http://127.0.0.1:8069"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
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

class ChatMessage(BaseModel):
    message: str = Field(..., description="The user's message to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the message")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Previous messages in the conversation")

    class Config:
        model = "claude-3-5-haiku-20241022"
        max_tokens = 2000
        temperature = 0.7

class DatabaseOperation(BaseModel):
    model: str = Field(..., description="The Odoo model to operate on")
    method: str = Field(..., description="The method to call on the model")
    args: List[Any] = Field(default_factory=list, description="Positional arguments for the method")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Keyword arguments for the method")

    class Config:
        model = "claude-3-5-haiku-20241022"
        max_tokens = 1000
        temperature = 0.3

@dataclass
class CRMContext:
    """Dependencies for the CRM agent"""
    # Odoo connection
    odoo_url: str
    odoo_db: str
    odoo_username: str
    odoo_password: str
    
    # CRM data
    leads: List[Dict[str, Any]] = field(default_factory=list)
    stages: List[Dict[str, Any]] = field(default_factory=list)
    teams: List[Dict[str, Any]] = field(default_factory=list)
    activity_types: List[Dict[str, Any]] = field(default_factory=list)
    activities: List[Dict[str, Any]] = field(default_factory=list)
    customers: List[Dict[str, Any]] = field(default_factory=list)
    
    # Services
    logger: logging.Logger = field(default_factory=lambda: logger)
    
    def __post_init__(self):
        """Fetch CRM data after initialization"""
        try:
            uid, models = self.get_odoo_connection()
            
            # Get leads and opportunities
            self.leads = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'crm.lead', 'search_read',
                [[]],
                {'fields': ['name', 'partner_id', 'type', 'stage_id', 'probability', 'expected_revenue', 'create_date', 'user_id']}
            )
            
            # Get pipeline stages
            self.stages = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'crm.stage', 'search_read',
                [[]],
                {'fields': ['name', 'sequence', 'is_won']}
            )
            
            # Get sales teams
            self.teams = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'crm.team', 'search_read',
                [[]],
                {'fields': ['name', 'member_ids', 'alias_id']}
            )
            
            # Get activity types
            self.activity_types = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'mail.activity.type', 'search_read',
                [[['res_model', '=', 'crm.lead']]],
                {'fields': ['name', 'category', 'delay_count', 'delay_unit']}
            )
            
            # Get recent activities
            self.activities = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'mail.activity', 'search_read',
                [[['res_model', '=', 'crm.lead']]],
                {'fields': ['res_id', 'activity_type_id', 'summary', 'date_deadline', 'user_id', 'state']}
            )
            
            # Get customer data
            self.customers = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                'res.partner', 'search_read',
                [[['customer_rank', '>', 0]]],
                {'fields': ['name', 'email', 'phone', 'street', 'city', 'country_id', 'customer_rank']}
            )
            
            self.logger.info(f"Retrieved CRM context with {len(self.leads)} leads, {len(self.stages)} stages, and {len(self.customers)} customers")
        except Exception as e:
            self.logger.error(f"Error fetching CRM data: {str(e)}")
            self.logger.error(f"Error type: {type(e)}")
            self.logger.error(f"Error args: {e.args}")
    
    def get_odoo_connection(self) -> tuple[int, Any]:
        """Establish connection to Odoo instance"""
        try:
            self.logger.info(f"Connecting to Odoo at {self.odoo_url} with database {self.odoo_db}")
            common = xmlrpc.client.ServerProxy(f'{self.odoo_url}/xmlrpc/2/common')
            uid = common.authenticate(self.odoo_db, self.odoo_username, self.odoo_password, {})
            if not uid:
                raise Exception("Authentication failed. Please check your credentials and database name.")
            models = xmlrpc.client.ServerProxy(f'{self.odoo_url}/xmlrpc/2/object')
            self.logger.info("Successfully connected to Odoo")
            return uid, models
        except Exception as e:
            self.logger.error(f"Error connecting to Odoo: {str(e)}")
            raise
    
    async def execute_database_operation(self, operation: DatabaseOperation) -> Any:
        """Execute a database operation safely"""
        try:
            self.logger.info(f"Executing database operation: {operation.model}.{operation.method}")
            self.logger.info(f"Args: {operation.args}")
            self.logger.info(f"Kwargs: {operation.kwargs}")
            
            uid, models = self.get_odoo_connection()
            
            # Execute the operation
            result = models.execute_kw(
                self.odoo_db, uid, self.odoo_password,
                operation.model,
                operation.method,
                operation.args,
                operation.kwargs
            )
            
            self.logger.info(f"Operation successful. Result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error executing database operation: {str(e)}")
            raise

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

async def test_anthropic_connection():
    """Test the connection to Anthropic API"""
    try:
        logger.info("Testing Anthropic API connection...")
        logger.info(f"API Key length: {len(ANTHROPIC_API_KEY)}")
        logger.info(f"API Key prefix: {ANTHROPIC_API_KEY[:10]}...")
        
        # Create a test model with the provider
        model = AnthropicModel(
            'claude-3-5-haiku-20241022',
            provider=AnthropicProvider(api_key=ANTHROPIC_API_KEY)
        )
        
        # Test the connection by creating a simple agent
        test_agent = Agent(model, deps_type=CRMContext, result_type=str)
        
        # Create a minimal context for testing
        test_context = CRMContext(
            odoo_url=ODOO_URL,
            odoo_db=ODOO_DB,
            odoo_username=ODOO_USERNAME,
            odoo_password=ODOO_PASSWORD
        )
        
        # Run a test message
        result = await test_agent.run(
            "Hello, this is a test message.",
            deps=test_context,
            usage_limits=UsageLimits(
                response_tokens_limit=100,
                request_limit=1
            )
        )
        
        logger.info("Anthropic API connection successful!")
        return True
    except Exception as e:
        logger.error(f"Anthropic API connection failed: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        return False

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
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        raise

class CRMAgent(Agent[CRMContext, str]):
    """AI agent specialized in CRM operations"""
    
    def __init__(self):
        # Initialize the Anthropic model
        model = AnthropicModel(
            'claude-3-5-haiku-20241022',
            provider=AnthropicProvider(api_key=ANTHROPIC_API_KEY)
        )
        
        # Initialize the agent with the model
        super().__init__(
            model,
            deps_type=CRMContext,
            result_type=str
        )
    
    @Agent.system_prompt
    async def get_system_prompt(self, ctx: RunContext[CRMContext]) -> str:
        """Generate the system prompt with current CRM context"""
        return f"""You are an AI assistant specialized in CRM operations for an Odoo ERP system. 
        Your primary focus is on managing customer relationships and sales opportunities. You can:
        1. Manage leads and opportunities:
           - Create, update, and track leads
           - Update opportunity stages and probabilities
           - Schedule follow-ups and activities
           - Assign leads to sales teams
        2. Handle customer information:
           - View and update customer details
           - Track customer interactions
           - Manage customer tags and segments
        3. Sales pipeline management:
           - Monitor pipeline stages
           - Update deal values and probabilities
           - Track conversion rates
           - Identify bottlenecks
        4. Activity management:
           - Schedule calls, meetings, and tasks
           - Set reminders and deadlines
           - Track activity completion
        5. Reporting and analytics:
           - Provide pipeline status updates
           - Analyze conversion rates
           - Track team performance
           - Identify trends and opportunities
        
        Current CRM Context:
        - Leads: {len(ctx.deps.leads)} active leads
        - Stages: {len(ctx.deps.stages)} pipeline stages
        - Teams: {len(ctx.deps.teams)} sales teams
        - Activities: {len(ctx.deps.activities)} recent activities
        - Customers: {len(ctx.deps.customers)} customers
        
        When making changes to the database, you should:
        1. First confirm the change with the user
        2. Use the appropriate model and method
        3. Provide clear feedback about what was changed
        
        Available CRM operations:
        - Lead/Opportunity Operations:
          * Create: {{"model": "crm.lead", "method": "create", "args": [[{{"name": "New Lead", "partner_id": 1, "type": "opportunity", "stage_id": 1}}]]}}
          * Update: {{"model": "crm.lead", "method": "write", "args": [[1], {{"probability": 100, "stage_id": 4}}]}}
          * Delete: {{"model": "crm.lead", "method": "unlink", "args": [[1]]}}
        
        - Activity Operations:
          * Create: {{"model": "mail.activity", "method": "create", "args": [[{{"res_model": "crm.lead", "res_id": 1, "activity_type_id": 1, "summary": "Call client"}}]]}}
          * Update: {{"model": "mail.activity", "method": "write", "args": [[1], {{"state": "done"}}]}}
        
        - Customer Operations:
          * Create: {{"model": "res.partner", "method": "create", "args": [[{{"name": "New Customer", "customer_rank": 1}}]]}}
          * Update: {{"model": "res.partner", "method": "write", "args": [[1], {{"email": "new@email.com"}}]}}
        
        Always format your responses in a clear, chat-friendly way using the following structure:
        
        [Brief summary of the opportunity and its current status]
        
        Here are the key details about this opportunity:
        • Name: [Opportunity name]
        • ID: [Opportunity ID]
        • Company: [Company name]
        • Contact: [Contact name]
        • Email: [Contact email]
        • Phone: [Contact phone]
        • Current Stage: [Stage name]
        • Probability: [Probability percentage]
        • Expected Revenue: [Revenue amount]
        
        [Analysis of the current stage and probability, explaining what it means for the sales process]
        
        Here are my recommended next steps:
        1. [First recommended action]
        2. [Second recommended action]
        3. [Third recommended action]
        
        [Clear call to action or question about what the user would like to do next]
        
        When providing information:
        - Use specific numbers and data from the context when available
        - Explain your reasoning when making suggestions
        - Highlight any potential issues or concerns
        - Suggest next steps when appropriate
        
        IMPORTANT: Maintain context from previous messages in the conversation. If the user refers to something 
        mentioned earlier (like a specific lead, customer, or activity), use that information to provide relevant responses."""
    
    async def process_message(self, message: str, context: Dict[str, Any], conversation_history: List[Dict[str, Any]] = None) -> str:
        """Process a message with context and conversation history"""
        try:
            # Create CRMContext with connection details
            crm_context = CRMContext(
                odoo_url=ODOO_URL,
                odoo_db=ODOO_DB,
                odoo_username=ODOO_USERNAME,
                odoo_password=ODOO_PASSWORD
            )
            
            # Run the agent with the message and context
            result = await self.run(
                message,
                deps=crm_context,
                usage_limits=UsageLimits(
                    response_tokens_limit=2000,
                    request_limit=5
                )
            )
            
            return result.data
        except Exception as e:
            logger.error(f"Error in agent processing: {str(e)}")
            raise

# Initialize the CRM agent
crm_agent = CRMAgent()

@app.get("/ping")
async def ping():
    """Test endpoint to verify service health"""
    try:
        # Test Anthropic API connection
        anthropic_connected = await test_anthropic_connection()
        
        # Test Odoo connection
        try:
            connect_to_odoo()
            odoo_connected = True
        except Exception as e:
            logger.error(f"Odoo connection failed: {str(e)}")
            odoo_connected = False
        
        return {
            "status": "ok",
            "anthropic_connected": anthropic_connected,
            "odoo_connected": odoo_connected
        }
    except Exception as e:
        logger.error(f"Ping test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(message: ChatMessage):
    """Process a chat message with the CRM agent"""
    try:
        # Process the message with the CRM agent
        response = await crm_agent.process_message(
            message.message,
            message.context,
            message.conversation_history
        )
        
        # Return success response
        return {
            "status": "success",
            "error": None,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        # Return error response with consistent format
        return {
            "status": "error",
            "error": str(e),
            "response": None
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 