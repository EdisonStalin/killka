# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.addons import decimal_precision as dp

class PosSession(models.Model):
    _inherit = 'pos.session'
    
    
    authorization_id = fields.Many2one('account.authorization', related='config_id.authorization_id', 
                                        string='Authorization', required=True, track_visibility='always')
    refund_authorization_id = fields.Many2one('account.authorization', related='config_id.refund_authorization_id', 
                                        string='Refund Authorization', track_visibility='always')
    check_refund = fields.Boolean(related='config_id.check_refund')
    untaxamount_total = fields.Float(string='Subtotal', compute='seetion_total', digits=dp.get_precision('Account Total'))
    tax_amount = fields.Float(string='Total VAT', compute='seetion_total', digits=dp.get_precision('Account Total'))
    subtotal_session = fields.Float(string='Total', compute='seetion_total', digits=dp.get_precision('Account Total'))
    number_of_order = fields.Integer(string='Total Order', compute='seetion_total')
    total_discount = fields.Float(string='Total discount', compute='seetion_total')
    sale_qty = fields.Integer(string='Total Qty Sale', compute='seetion_total')
    total_done_order = fields.Integer(string='Total Done Order', compute='seetion_total')
    total_cancel_order = fields.Integer(string='Total Cancel Order', compute='seetion_total')


    @api.depends('order_ids.state', 'state')
    def seetion_total(self):
        for rec in self.filtered(lambda s: s.state in ['opened','closing_control']):
            subtotal_session = untaxamount_total = 0.0
            sale_qty = 0
            rec.number_of_order = len(rec.order_ids)
            rec.total_cancel_order = len(rec.order_ids.filtered(lambda o: o.state=='cancel'))
            orders_done = rec.order_ids.filtered(lambda o: o.state in ['paid','done','invoiced'])
            orders_invoice = rec.order_ids.filtered(lambda o: o.state in ['invoiced'])
            rec.total_done_order = len(orders_invoice)
            rec.tax_amount = sum(order.amount_tax for order in orders_done)
            rec.total_discount = sum(order.amount_discount for order in orders_done)
            for order in orders_done:
                subtotal_session += sum(line.price_subtotal_incl for line in order.lines)
                untaxamount_total += sum(line.price_subtotal for line in order.lines)
                sale_qty += sum(line.qty for line in order.lines)
            rec.subtotal_session = subtotal_session
            rec.untaxamount_total = untaxamount_total
            rec.sale_qty = sale_qty
