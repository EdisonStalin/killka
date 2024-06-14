# -*- coding: utf-8 -*-

from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

        
    vat_accountant = fields.Many2one('res.partner', string='Vat Accountant', size=13, help='Identification of accountant')
    vat_legal = fields.Many2one('res.partner', string='Vat Legal', size=13, help='Identification of legal representative')
    tip_rate = fields.Float(string='Tip Rate', digits=(10, 2), default=10.0, help='Tip Rate apply in invoice')
    refund_product_id = fields.Many2one('product.product', string="Refund product")

    property_account_receivable_id = fields.Many2one('account.account', string="Default Sale Account", 
                                                     domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_receivable').id), ('deprecated', '=', False)])
    property_account_payable_id = fields.Many2one('account.account', string="Default Purchase Account", 
                                                  domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_payable').id), ('deprecated', '=', False)])    
    property_account_expense_id = fields.Many2one('account.account', string="Default Product Expense")
    property_account_income_id = fields.Many2one('account.account', string="Default Product Income")
    property_receivable_journal_id = fields.Many2one('account.journal', string="Default Sale Journal")
    property_payable_journal_id = fields.Many2one('account.journal', string="Default Purchase Journal")
