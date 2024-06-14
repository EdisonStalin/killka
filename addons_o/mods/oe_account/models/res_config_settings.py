# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    

    property_receivable_journal_id = fields.Many2one('account.journal', related='company_id.property_receivable_journal_id', string="Default Sale Journal")
    property_payable_journal_id = fields.Many2one('account.journal', related='company_id.property_payable_journal_id', string="Default Purchase Journal")
    property_account_receivable_id = fields.Many2one('account.account', related='company_id.property_account_receivable_id', string="Default Sale Account")
    property_account_payable_id = fields.Many2one('account.account', related='company_id.property_account_payable_id', string="Default Purchase Account")
    property_account_income_id = fields.Many2one('account.account', related='company_id.property_account_income_id', string="Default Product Income")
    property_account_expense_id = fields.Many2one('account.account', related='company_id.property_account_expense_id', string="Default Product Expense")
    transfer_account_id = fields.Many2one('account.account', related='company_id.transfer_account_id', string="Transfer Account")
    tip_rate = fields.Float(related='company_id.tip_rate', string="Tip Rate")
    refund_product_id = fields.Many2one(related='company_id.refund_product_id', string="Refund product")

