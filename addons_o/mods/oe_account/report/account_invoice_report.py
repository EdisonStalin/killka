# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'
    _auto = False
    
    type_document_id = fields.Many2one('account.type.document', string='Voucher type', readonly=True)
    method_id = fields.Many2one('account.method.payment', string='Payment Method', readonly=True)
    is_electronic = fields.Boolean(readonly=True)
    message_state = fields.Char(string='Message Authorization', readonly=True)
    amount_total = fields.Float(string='Total Amount', readonly=True)
    amount_tax = fields.Float(string='Total Tax Amount', readonly=True)
    

    def _select(self):
        select_str = super(AccountInvoiceReport, self)._select()
        select_str += """,
            sub.type_document_id,
            sub.method_id,
            sub.is_electronic,
            sub.message_state,
            sub.amount_tax AS amount_tax,
            sub.amount_total AS amount_total
        """
        return select_str

    
    def _sub_select(self):
        select_str = super(AccountInvoiceReport, self)._sub_select()
        select_str += """,
            ai.type_document_id,
            ai.method_id,
            ai.is_electronic,
            ai.message_state,
            SUM(ail.price_tax) AS amount_tax,
            SUM(ail.price_total) AS amount_total
        """
        return select_str


    def _group_by(self):
        group_by_str = super(AccountInvoiceReport, self)._group_by()
        group_by_str += """,
            ai.type_document_id,
            ai.method_id,
            ai.is_electronic,
            ai.message_state
        """
        return group_by_str
    
