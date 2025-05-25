"""
Configuration settings for the Odoo ERP AI Agent API wrapper
"""
import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API settings
API_VERSION = os.getenv("API_VERSION", "1.0.0")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true"
API_PREFIX = os.getenv("API_PREFIX", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
JSON_LOGS = os.getenv("JSON_LOGS", "false").lower() == "true"

# CORS settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8069,http://localhost:3000").split(",")

# Security settings
API_KEYS = os.getenv("API_KEYS", "").split(",")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour in seconds

# Odoo connection settings
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "HISEY")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "cjhisey@gmail.com")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "odoo")
ODOO_API_KEY = os.getenv("ODOO_API_KEY", "")

# AI Agent settings
AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://localhost:8000")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Webhook settings
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"
WEBHOOK_URLS = os.getenv("WEBHOOK_URLS", "").split(",")

# Timeout settings
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))  # 30 seconds
LONG_TIMEOUT = int(os.getenv("LONG_TIMEOUT", "120"))  # 2 minutes

# Cache settings
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes

# Feature flags
FEATURE_BATCH_OPERATIONS = os.getenv("FEATURE_BATCH_OPERATIONS", "true").lower() == "true"
FEATURE_WEBHOOKS = os.getenv("FEATURE_WEBHOOKS", "true").lower() == "true"
FEATURE_ASYNC_OPERATIONS = os.getenv("FEATURE_ASYNC_OPERATIONS", "true").lower() == "true"

# Export all settings as a dictionary
def get_settings() -> Dict[str, Any]:
    """Get all settings as a dictionary"""
    return {k: v for k, v in globals().items() 
            if not k.startswith('_') and k.isupper()}
