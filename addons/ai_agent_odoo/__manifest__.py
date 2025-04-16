{
    'name': 'AI Agent Integration',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Integrates AI Agent with Odoo',
    'description': """
        This module integrates the AI Agent with Odoo, providing a chat interface
        for interacting with the AI assistant and sales agent.
    """,
    'author': 'Your Company',
    'website': '',
    'depends': ['base', 'web', 'mail', 'crm'],
    'data': [
        'views/ai_agent_views.xml',
        'views/sales_agent_views.xml',
        'views/menu_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_agent_odoo/static/src/js/ai_agent.js',
            'ai_agent_odoo/static/src/css/ai_agent.css',
            'ai_agent_odoo/static/src/xml/ai_agent.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
} 