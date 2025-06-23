from odoo import models, fields, api
import requests
import json
import os

class AIAgent(models.Model):
    _name = 'ai.agent'
    _description = 'AI Agent'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', default='AI Assistant', required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived')
    ], default='active', string='Status')
    
    @api.model
    def send_message(self, message):
        """Send a message to the AI agent and get the response"""
        try:
            # Get the AI agent URL from environment variable or use default
            ai_agent_url = os.getenv('AI_AGENT_URL', 'http://localhost:8000')
            response = requests.post(
                f'{ai_agent_url}/chat',
                json={'message': message},
                timeout=30  # Add timeout to prevent hanging
            )
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                return f"Error: {response.status_code} - {response.text}"
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to AI agent service. Please make sure it's running."
        except Exception as e:
            return f"Error: {str(e)}" 