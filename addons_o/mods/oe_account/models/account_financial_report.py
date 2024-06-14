# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountFinancialReport(models.Model):
    _inherit = 'account.financial.report'
    
    beginning_balance = fields.Boolean('Include Beginning Balance', help='You will present values ​​including initial balances')
