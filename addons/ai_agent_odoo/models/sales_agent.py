from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SalesAgent(models.Model):
    _name = 'sales.agent'
    _description = 'Sales Agent'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Email', required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline')
    ], default='available', string='Status')
    
    # Email templates
    email_templates = fields.One2many(
        'sales.agent.email.template',
        'agent_id',
        string='Email Templates'
    )
    
    # Communication history
    communication_history = fields.One2many(
        'sales.agent.communication',
        'agent_id',
        string='Communication History'
    )

    @api.model
    def process_instruction(self, instruction):
        """Process instructions from the main AI agent"""
        try:
            _logger.info(f"Sales agent received instruction: {instruction}")
            
            # Parse the instruction
            if instruction.get('type') == 'email':
                return self._handle_email_instruction(instruction)
            elif instruction.get('type') == 'follow_up':
                return self._handle_follow_up_instruction(instruction)
            else:
                return {"status": "error", "message": "Unknown instruction type"}
                
        except Exception as e:
            _logger.error(f"Error processing instruction: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _handle_email_instruction(self, instruction):
        """Handle email-related instructions"""
        try:
            # Get the customer
            customer = self.env['res.partner'].browse(instruction.get('customer_id'))
            if not customer:
                return {"status": "error", "message": "Customer not found"}

            # Get or create email template
            template = self._get_or_create_template(instruction.get('template_name'))
            
            # Prepare email values
            email_values = {
                'email_to': customer.email,
                'subject': instruction.get('subject', template.subject),
                'body_html': instruction.get('body', template.body),
                'model': 'res.partner',
                'res_id': customer.id,
            }
            
            # Send the email
            mail = self.env['mail.mail'].create(email_values)
            mail.send()
            
            # Record the communication
            self.env['sales.agent.communication'].create({
                'agent_id': self.id,
                'customer_id': customer.id,
                'type': 'email',
                'content': instruction.get('body'),
                'status': 'sent'
            })
            
            return {"status": "success", "message": "Email sent successfully"}
            
        except Exception as e:
            _logger.error(f"Error sending email: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _get_or_create_template(self, template_name):
        """Get existing template or create a new one"""
        template = self.env['sales.agent.email.template'].search([
            ('name', '=', template_name),
            ('agent_id', '=', self.id)
        ], limit=1)
        
        if not template:
            template = self.env['sales.agent.email.template'].create({
                'name': template_name,
                'agent_id': self.id,
                'subject': f"Template: {template_name}",
                'body': "Default template body"
            })
            
        return template

class SalesAgentEmailTemplate(models.Model):
    _name = 'sales.agent.email.template'
    _description = 'Sales Agent Email Template'

    name = fields.Char(string='Name', required=True)
    agent_id = fields.Many2one('sales.agent', string='Agent', required=True)
    subject = fields.Char(string='Subject')
    body = fields.Html(string='Body')

class SalesAgentCommunication(models.Model):
    _name = 'sales.agent.communication'
    _description = 'Sales Agent Communication History'

    agent_id = fields.Many2one('sales.agent', string='Agent', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    type = fields.Selection([
        ('email', 'Email'),
        ('call', 'Phone Call'),
        ('meeting', 'Meeting')
    ], string='Type', required=True)
    content = fields.Text(string='Content')
    status = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('scheduled', 'Scheduled')
    ], string='Status', default='sent')
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now()) 