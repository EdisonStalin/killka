# -*- coding: utf-8 -*-

from odoo import models, fields

class Message(models.Model):
    _inherit = 'mail.template'
    
    active = fields.Boolean(default=True, help="Set active to false to hide the template without removing it.")