# Odoo Docker Setup Guide

## Prerequisites
This setup runs in WSL with docker-compose.

## Installation Steps

1. Update and install required packages:
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
docker-compose build ai_agent
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
Note: You need to provide your own Anthropic API key or implement your preferred LLM API service in the app.py file.