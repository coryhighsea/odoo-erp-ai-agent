# Odoo ERP AI Agent with REST API Wrapper

A comprehensive REST API wrapper for the Odoo AI Agent application, designed for n8n workflows and other external integrations.

## Overview

This project consists of two main components:

1. **Odoo AI Agent** - A Python application that connects to Odoo ERP and uses AI to provide intelligent responses and actions
2. **REST API Wrapper** - A FastAPI-based REST API that makes the AI Agent accessible to external applications

## Prerequisites

- Python 3.8+
- Odoo ERP instance (running locally or remotely)
- Anthropic API key for Claude AI model
- Docker and docker-compose (for containerized deployment)

## Installation

### Option 1: Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/odoo-erp-ai-agent.git
cd odoo-erp-ai-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration:
```
# API Settings
API_HOST=0.0.0.0
API_PORT=8080
API_VERSION=1.0.0
ENVIRONMENT=development

# Odoo Connection
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=admin

# AI Agent Settings
AI_AGENT_URL=http://localhost:8000
ANTHROPIC_API_KEY=your_anthropic_api_key

# Security
API_KEYS=your_api_key_here
```

4. Start the API server:
```bash
python main.py
```

### Option 2: Docker Deployment

1. Update and install required packages (if needed):
```bash
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable --now docker
```

2. Configure Docker permissions (if needed):
```bash
getent group docker
sudo usermod -aG docker $USER
newgrp docker
```

3. Start the server:
```bash
docker-compose up -d
```

## API Documentation

Once the API is running, you can access the interactive documentation at:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## API Endpoints

### Agent Endpoints

- `POST /agent/query` - Send queries to the Odoo AI agent
- `GET /agent/status` - Check agent status and health
- `GET/POST/DELETE /agent/sessions` - Manage conversation sessions
- `GET /agent/history/{session_id}` - Retrieve conversation history

### Odoo Endpoints

- `POST /odoo/connect` - Test/establish Odoo connection
- `GET /odoo/models` - List available Odoo models
- `POST /odoo/execute` - Execute specific Odoo operations
- `GET /odoo/schema/{model_name}` - Get schema for a specific model
- `GET /odoo/records/{model_name}` - Get records for a specific model

### System Endpoints

- `GET /health` - Check API health status
- `GET /health/ping` - Simple ping endpoint
- `GET /health/detailed` - Detailed health information (requires API key)

## n8n Integration

To use this API with n8n workflows:

1. Use the HTTP Request node in n8n
2. Set the appropriate endpoint URL
3. Add the `X-API-Key` header with your API key
4. Configure the request method and body as needed

Example n8n HTTP Request configuration for querying the AI agent:

```json
{
  "url": "http://your-api-host:8080/agent/query",
  "method": "POST",
  "headers": {
    "X-API-Key": "your_api_key_here",
    "Content-Type": "application/json"
  },
  "body": {
    "message": "What is the current inventory status?",
    "include_history": true
  }
}
```

## Server Management

### Starting the Server
```bash
docker-compose up -d
```

### Stopping the Server
```bash
docker-compose down
```

### Building Specific Services
```bash
docker-compose build api
```

### Soft Start/Stop
```bash
# Stop services
docker-compose stop

# Start services
docker-compose start
```

### Complete Reset
To shutdown and delete the database for a full restart:
```bash
docker-compose down -v
```

## API Configuration
Note: You need to provide your own Anthropic API key in the .env file or as an environment variable.