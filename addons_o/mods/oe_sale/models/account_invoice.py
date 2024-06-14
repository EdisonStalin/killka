# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    sale_id = fields.Many2one(comodel_name='sale.order', string='Add Sale Order', readonly=True, states={'draft': [('readonly', False)]},
        help='Encoding help. When selected, the associated sale order lines are added to the vendor bill. Several PO can be selected.'
    )


    @api.onchange('state', 'partner_id', 'invoice_line_ids')
    def _onchange_allowed_sale_ids(self):
        '''
        The purpose of the method is to define a domain for the available
        sale orders.
        '''
        result = {}

        # A PO can be selected only if at least one PO line is not already in the invoice
        purchase_line_ids = self.invoice_line_ids.mapped('purchase_line_id')
        purchase_ids = self.invoice_line_ids.mapped('purchase_id').filtered(lambda r: r.order_line <= purchase_line_ids)

        domain = [('invoice_status', '=', 'to invoice')]
        if self.partner_id:
            domain += [('partner_id', 'child_of', self.partner_id.id)]
        if purchase_ids:
            domain += [('id', 'not in', purchase_ids.ids)]
        result['domain'] = {'purchase_id': domain}
        return result

