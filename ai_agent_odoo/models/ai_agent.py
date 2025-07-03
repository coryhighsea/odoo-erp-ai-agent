# -*- coding: utf-8 -*-
from odoo import models

# We are creating a placeholder model because the original views referred to it.
# For a pure JavaScript widget, this isn't strictly necessary, but it's good practice
# to keep the file structure. No fields or methods are needed here for now.
class AIAgent(models.Model):
    _name = 'ai.agent'
    _description = 'AI Assistant Configuration (Placeholder)'