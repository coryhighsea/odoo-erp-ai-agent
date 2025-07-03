# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class AIAgentController(http.Controller):

    @http.route('/ai_agent/get_config', type='json', auth='user')
    def get_config(self):
        """
        Securely provides the AI Agent service URL to the frontend.
        The URL is stored in Odoo's System Parameters for easy configuration.
        """
        get_param = request.env['ir.config_parameter'].sudo().get_param
        ai_agent_url = get_param('ai_agent.service_url')
        ai_agent_api_key = get_param('ai_agent.api_key')
        return {
            'ai_agent_url': ai_agent_url,
            'ai_agent_api_key': ai_agent_api_key,
        }