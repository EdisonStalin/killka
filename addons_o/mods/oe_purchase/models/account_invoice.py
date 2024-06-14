# -*- coding: utf-8 -*-

from odoo import models

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'


    def _prepare_invoice_line_from_po_line(self, line):
        vals = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        vals.update({
            'type_discount': line.type_discount,
            'discount': line.discount,
        })
        return vals
