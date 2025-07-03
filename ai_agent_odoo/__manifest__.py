{
    'name': "AI Assistant",
    'version': '18.0.2.0.0',
    'category': 'Tools',
    'summary': "Integrates a powerful AI assistant into the Odoo interface.",
    'description': """
        This module provides a floating chat widget to interact with a backend AI service,
        allowing users to ask questions and trigger actions within Odoo.
    """,
    'license': 'LGPL-3',
    'author': 'Cory Hisey',
    'website': 'https://coryhisey.com',
    'depends': ['web', 'mail'],  # 'base' is included with 'web', so it's not strictly needed here

    'assets': {
        'web.assets_backend': [
            # Corrected paths relative to the addon root directory
            'ai_agent_odoo/static/src/css/ai_agent.css',
            'ai_agent_odoo/static/src/js/ai_agent.js',
            'ai_agent_odoo/static/src/xml/ai_agent.xml',
            'ai_agent_odoo/static/src/js/lib/marked.min.js',
            'ai_agent_odoo/static/src/js/lib/dompurify.min,js',
        ],
    },
    'images': ['static/images/thumbnail.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
