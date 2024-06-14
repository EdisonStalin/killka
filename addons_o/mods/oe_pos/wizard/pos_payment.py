# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.addons import decimal_precision as dp
from odoo.tools import float_is_zero, float_compare

class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'


    def _default_amount(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            return (order.amount_total - order.amount_paid)
        return False


    amount = fields.Float(digits=dp.get_precision('Account Total'), required=True, default=_default_amount)


    @api.multi
    def check(self):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        self.ensure_one()
        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        currency = order.pricelist_id.currency_id
        amount = order.amount_total - order.amount_paid
        data = self.read()[0]
        # add_payment expect a journal key
        data['journal'] = data['journal_id'][0]
        data['amount'] = currency.round(data['amount'])\
            if currency and float_compare(amount, data['amount'], precision_rounding=currency.rounding) else data['amount']
        if not float_is_zero(amount, precision_rounding=currency.rounding or 0.01):
            order.add_payment(data)
        if order.test_paid():
            order.action_pos_order_paid()
            return {'type': 'ir.actions.act_window_close'}
        return self.launch_payment()
