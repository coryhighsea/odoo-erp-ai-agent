from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import os
from dotenv import load_dotenv
import xmlrpc.client
import anthropic
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8069"],  # Odoo frontend URL
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

class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None
    conversation_history: Optional[List[dict]] = None

class DatabaseOperation(BaseModel):
    model: str
    method: str
    args: List[Any]
    kwargs: Dict[str, Any]

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

def get_odoo_context():
    """Get current context from Odoo"""
    try:
        logger.info("Connecting to Odoo...")
        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        logger.info("Fetching CRM data...")
        context = {}
        
        # Get CRM-specific data
        try:
            # Get leads and opportunities
            leads = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                'crm.lead', 'search_read',
                [[]],
                {'fields': ['name', 'partner_id', 'type', 'stage_id', 'probability', 'expected_revenue', 'create_date', 'user_id']})
            context['leads'] = leads
            
            # Get pipeline stages - removed is_lost field as it's not available
            stages = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                'crm.stage', 'search_read',
                [[]],
                {'fields': ['name', 'sequence', 'is_won']})
            context['stages'] = stages
            
            # Get sales teams
            teams = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                'crm.team', 'search_read',
                [[]],
                {'fields': ['name', 'member_ids', 'alias_id']})
            context['teams'] = teams
            
            # Get activity types
            activity_types = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                'mail.activity.type', 'search_read',
                [[['res_model', '=', 'crm.lead']]],
                {'fields': ['name', 'category', 'delay_count', 'delay_unit']})
            context['activity_types'] = activity_types
            
            # Get recent activities
            activities = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                'mail.activity', 'search_read',
                [[['res_model', '=', 'crm.lead']]],
                {'fields': ['res_id', 'activity_type_id', 'summary', 'date_deadline', 'user_id', 'state']})
            context['activities'] = activities
            
            # Get customer data
            customers = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'search_read',
                [[['customer_rank', '>', 0]]],
                {'fields': ['name', 'email', 'phone', 'street', 'city', 'country_id', 'customer_rank']})
            context['customers'] = customers
            
        except Exception as e:
            logger.error(f"Error fetching CRM data: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
        
        logger.info(f"Retrieved CRM context: {context}")
        return context
    except Exception as e:
        logger.error(f"Error getting Odoo context: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        return {}

def test_anthropic_connection():
    """Test the connection to Anthropic API"""
    try:
        logger.info("Testing Anthropic API connection...")
        logger.info(f"API Key length: {len(ANTHROPIC_API_KEY)}")
        logger.info(f"API Key prefix: {ANTHROPIC_API_KEY[:10]}...")
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello, this is a test message."}
            ]
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

def process_with_llm(message: str, context: dict, conversation_history: List[dict] = None):
    """Process the message with Claude and return a response"""
    try:
        logger.info("Initializing Anthropic client...")
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Convert context to a readable format
        context_str = ""
        if context:
            for section, data in context.items():
                context_str += f"\n{section.upper()}:\n"
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            context_str += "- " + ", ".join(f"{k}: {v}" for k, v in item.items()) + "\n"
                        else:
                            context_str += f"- {item}\n"
                elif isinstance(data, dict):
                    context_str += "- " + ", ".join(f"{k}: {v}" for k, v in data.items()) + "\n"
                else:
                    context_str += f"- {data}\n"
        
        logger.info(f"Formatted context being sent to LLM: {context_str}")
        
        system_prompt = f"""You are an AI assistant specialized in CRM operations for an Odoo ERP system. 
        You have access to the following context about the system:
        {context_str}
        
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
        
        # Prepare messages array with conversation history
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        logger.info("Sending request to Anthropic API...")
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2000,
            system=system_prompt,
            messages=messages
        )
        logger.info("Received response from Anthropic API")
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error in LLM processing: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        raise

@app.get("/ping")
async def ping():
    """Test endpoint to verify service health"""
    try:
        # Test Anthropic API connection
        anthropic_connected = test_anthropic_connection()
        
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
    try:
        logger.info(f"Received chat message: {message.message}")
        logger.info(f"Message context: {message.context}")
        logger.info(f"Conversation history: {message.conversation_history}")
        
        # Get current Odoo context
        logger.info("Fetching Odoo context...")
        context = get_odoo_context()
        logger.info(f"Retrieved Odoo context: {context}")
        
        # Process the message with LLM
        logger.info("Processing message with LLM...")
        response = process_with_llm(message.message, context, message.conversation_history)
        
        # Check if the response contains a database operation
        try:
            if "DATABASE_OPERATION:" in response:
                operation_json = response.split("DATABASE_OPERATION:")[1].strip()
                operation = DatabaseOperation(**json.loads(operation_json))
                result = execute_database_operation(operation)
                response = response.split("DATABASE_OPERATION:")[0] + f"\nOperation successful: {result}"
        except Exception as e:
            logger.error(f"Error executing database operation: {str(e)}")
            response = f"Error executing database operation: {str(e)}"
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 