from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import xmlrpc.client
import anthropic
import logging

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
        
        logger.info("Fetching data...")
        context = {}
        
        # Check which modules are installed
        installed_modules = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
            'ir.module.module', 'search_read',
            [[['state', '=', 'installed']]],
            {'fields': ['name']})
        installed_module_names = [m['name'] for m in installed_modules]
        logger.info(f"Installed modules: {installed_module_names}")
        
        # Always include inventory data as it's part of the base system
        try:
            context['inventory'] = {
                'products': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                    'product.product', 'search_read',
                    [[['type', '=', 'product']]],
                    {'fields': ['name', 'qty_available', 'virtual_available', 'standard_price']}),
                'categories': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                    'product.category', 'search_read',
                    [[]],
                    {'fields': ['name', 'parent_id']}),
            }
        except Exception as e:
            logger.error(f"Error fetching inventory data: {str(e)}")
        
        # Include manufacturing data if mrp module is installed
        if 'mrp' in installed_module_names:
            try:
                context['manufacturing'] = {
                    'boms': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'mrp.bom', 'search_read',
                        [[]],
                        {'fields': ['product_tmpl_id', 'product_qty', 'code']}),
                    'workcenters': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'mrp.workcenter', 'search_read',
                        [[]],
                        {'fields': ['name', 'resource_calendar_id', 'time_efficiency']}),
                    'production_orders': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'mrp.production', 'search_read',
                        [[['state', 'in', ['draft', 'confirmed', 'progress']]]],
                        {'fields': ['name', 'product_id', 'product_qty', 'state']}),
                }
            except Exception as e:
                logger.error(f"Error fetching manufacturing data: {str(e)}")
        
        # Include sales data if sale module is installed
        if 'sale' in installed_module_names:
            try:
                context['sales'] = {
                    'orders': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'sale.order', 'search_read',
                        [[['state', 'in', ['draft', 'sent', 'sale']]]],
                        {'fields': ['name', 'partner_id', 'amount_total', 'state', 'date_order']}),
                    'order_lines': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'sale.order.line', 'search_read',
                        [[['order_id.state', 'in', ['draft', 'sent', 'sale']]]],
                        {'fields': ['order_id', 'product_id', 'product_uom_qty', 'price_unit', 'price_subtotal']}),
                    'customers': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'res.partner', 'search_read',
                        [[['customer_rank', '>', 0]]],
                        {'fields': ['name', 'email', 'phone', 'street', 'city', 'country_id']}),
                }
            except Exception as e:
                logger.error(f"Error fetching sales data: {str(e)}")
        
        # Include purchasing data if purchase module is installed
        if 'purchase' in installed_module_names:
            try:
                context['purchasing'] = {
                    'orders': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'purchase.order', 'search_read',
                        [[['state', 'in', ['draft', 'sent', 'purchase']]]],
                        {'fields': ['name', 'partner_id', 'amount_total', 'state', 'date_order', 'date_planned']}),
                    'order_lines': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'purchase.order.line', 'search_read',
                        [[['order_id.state', 'in', ['draft', 'sent', 'purchase']]]],
                        {'fields': ['order_id', 'product_id', 'product_qty', 'price_unit', 'price_subtotal']}),
                    'suppliers': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'res.partner', 'search_read',
                        [[['supplier_rank', '>', 0]]],
                        {'fields': ['name', 'email', 'phone', 'street', 'city', 'country_id']}),
                }
            except Exception as e:
                logger.error(f"Error fetching purchasing data: {str(e)}")
        
        # Include accounting data if account module is installed
        if 'account' in installed_module_names:
            try:
                context['accounting'] = {
                    'invoices': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'account.move', 'search_read',
                        [[['move_type', 'in', ['out_invoice', 'in_invoice']], ['state', '!=', 'cancel']]],
                        {'fields': ['name', 'partner_id', 'amount_total', 'state', 'invoice_date', 'invoice_date_due', 'payment_state']}),
                    'invoice_lines': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'account.move.line', 'search_read',
                        [[['move_id.move_type', 'in', ['out_invoice', 'in_invoice']], ['move_id.state', '!=', 'cancel']]],
                        {'fields': ['move_id', 'product_id', 'quantity', 'price_unit', 'price_subtotal']}),
                    'payments': models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                        'account.payment', 'search_read',
                        [[['state', '!=', 'cancel']]],
                        {'fields': ['name', 'partner_id', 'amount', 'payment_type', 'date', 'state']}),
                }
            except Exception as e:
                logger.error(f"Error fetching accounting data: {str(e)}")
        
        logger.info(f"Retrieved context: {context}")
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

def process_with_llm(message: str, context: dict):
    """Process the message with Claude and return a response"""
    try:
        logger.info("Initializing Anthropic client...")
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Convert context to a readable format
        context_str = ""
        if context:
            for section, data in context.items():
                context_str += f"\n{section.upper()}:\n"
                for key, items in data.items():
                    context_str += f"\n{key}:\n"
                    if isinstance(items, list):
                        for item in items:
                            context_str += f"- {item}\n"
                    else:
                        context_str += f"- {items}\n"
        
        logger.info(f"Formatted context being sent to LLM: {context_str}")
        
        system_prompt = f"""You are an AI assistant for an Odoo ERP system. 
        You have access to the following context about the system:
        {context_str}
        
        Your task is to help users with their ERP operations. You can:
        1. Answer questions about inventory levels, products, and categories
        2. Help with manufacturing processes, BOMs, and work centers
        3. Provide information about sales orders and customers
        4. Assist with purchase orders and supplier information
        5. Help with accounting, invoices, and payments
        6. Provide insights about the data and suggest actions
        7. Analyze relationships between different aspects of the business
        
        Always be professional and precise in your responses. When providing information:
        - Use specific numbers and data from the context when available
        - Explain your reasoning when making suggestions
        - Highlight any potential issues or concerns
        - Suggest next steps when appropriate"""
        
        logger.info("Sending request to Anthropic API...")
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": message}
            ]
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
        
        # Get current Odoo context
        logger.info("Fetching Odoo context...")
        context = get_odoo_context()
        logger.info(f"Retrieved Odoo context: {context}")
        
        # Process the message with LLM
        logger.info("Processing message with LLM...")
        response = process_with_llm(message.message, context)
        logger.info("Successfully processed message")
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 