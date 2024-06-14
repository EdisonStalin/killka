# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountingFinanceReportOutputWizard(models.TransientModel):
    _name = 'accounting.finance.report.output.wizard'
    _description = 'Wizard to store the Excel output'

    xls_output = fields.Binary(string='Excel Output')
    name = fields.Char(string='File Name', help='Save report as .xls format', default='Trial_Balance.xls')