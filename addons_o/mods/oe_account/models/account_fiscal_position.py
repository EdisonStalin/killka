# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'
    
    code = fields.Char(string='Withholding Agent', size=8, help='Resolution number, omitting the zeros to the left.')
    agent = fields.Boolean(string='Agent Withhold', help='Activate the withholding agent option.')
    option = fields.Selection(selection=[('none', 'None'), ('micro', 'Micro Businesses'),
                                         ('rimpe', 'RIMPE')], string='Presentation in XML', default='none',
                                         help='In the XML electronic vouchers the legends were added.')
