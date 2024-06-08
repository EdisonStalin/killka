# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'
    
    xls_output = fields.Binary(string='Excel Output')
    name = fields.Char(string='File Name', help='Save report as .xls format', default='Trial_Balance.xls')