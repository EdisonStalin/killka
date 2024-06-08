# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.addons.decimal_precision as dp
from odoo.tools import float_round

READONLY_STATES = {
    'draft': [('readonly', True)],
    'sent': [('readonly', True)],
}

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    @api.depends('details_tax', 'order_line.product_qty', 'order_line.price_unit')
    def _amount_all(self):
        super(PurchaseOrder, self)._amount_all()
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            base_taxed = base_taxed_0 = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_discount += line.discount if line.type_discount=='fixed' else (line.price_unit * line.discount)/100
                base_taxed_0 += line.price_subtotal if line.price_tax == 0.0 else 0.0
                base_taxed += line.price_subtotal if line.price_tax > 0.0 else 0.0
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed + amount_discount,
                'amount_discount': amount_discount,
                'amount_subtotal': amount_untaxed,
                'base_taxed_0': base_taxed_0,
                'base_taxed': base_taxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })


    user_id = fields.Many2one('res.users', string='Responsible', required=True, readonly=True,
                                states=READONLY_STATES, default=lambda self: self.env.user)
    approved_uid = fields.Many2one('res.users', string='Approved by', required=True, readonly=True,
                                states=READONLY_STATES, default=lambda self: self.env.user)
    details_tax = fields.Boolean('Details Tax', copy=False)
    amount_discount = fields.Float(string='Discount', store=True, readonly=True, digits=dp.get_precision('APU Line Total'),
        default=0.0, compute='_amount_all', track_visibility='always')
    amount_subtotal = fields.Float(string='Subtotal', store=True, readonly=True, digits=dp.get_precision('APU Line Total'),
        default=0.0, compute='_amount_all', track_visibility='always')
    base_taxed_0 = fields.Float(string='Tax Base 0', store=True, readonly=True, digits=dp.get_precision('APU Line Total'),
        default=0.0, compute='_amount_all', track_visibility='always')
    base_taxed = fields.Float(string='Tax Base difference of 0%', store=True, readonly=True, digits=dp.get_precision('APU Line Total'),
        default=0.0, compute='_amount_all', track_visibility='always')

    
    @api.model
    def default_get(self, default_fields):
        res = super(PurchaseOrder, self).default_get(default_fields)
        if 'date_planned' not in res:
            res['date_planned'] = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'


    @api.depends('type_discount', 'discount')
    def _compute_amount(self):
        for line in self:
            price_unit = False
            # This is always executed for allowing other modules to use this
            # with different conditions than discount != 0
            price = line._get_discounted_price_unit()
            if price != line.price_unit:
                # Only change value if it's different
                price_unit = line.price_unit
                line.price_unit = price
            super(PurchaseOrderLine, line)._compute_amount()
            if price_unit:
                line.price_unit = price_unit

    available_qty = fields.Float(string='Available Qty', digits=dp.get_precision('Product Unit of Measure'), default=0)
    last_cost = fields.Float(string='Last Cost', digits=dp.get_precision('Product Price'),
        default=0,help='Current Last Cost')
    type_discount = fields.Selection(default='percent', required=True,
        selection=[('fixed', 'Fixed'), ('percent', 'Percentage')])
    discount = fields.Float(string='Discount', digits=dp.get_precision('Discount'))

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
            result.update({'value': {
                'available_qty': self.product_id.qty_available,
                'last_cost': self.product_id.last_cost
            }})
        return result
    
    def _get_discounted_price_unit(self):
        """Inheritable method for getting the unit price after applying
        discount(s).

        :rtype: float
        :return: Unit price after discount(s).
        """
        self.ensure_one()
        prodig = self.env['decimal.precision'].precision_get('Product Price')
        disdig = self.env['decimal.precision'].precision_get('Discount')
        if self.discount and self.type_discount=='percent':
            return self.price_unit * (1 - self.discount / 100)
        elif self.discount and self.type_discount=='fixed':
            subtotal = self.price_unit * self.product_qty
            discount = float_round((self.discount * 100) / subtotal, precision_digits=disdig)
            price_unit = self.price_unit * (1 - discount / 100)
            return float_round(price_unit, precision_digits=prodig)
        return self.price_unit


    @api.multi
    def _get_stock_move_price_unit(self):
        """Get correct price with discount replacing current price_unit
        value before calling super and restoring it later for assuring
        maximum inheritability.
        """
        price_unit = False
        price = self._get_discounted_price_unit()
        if price != self.price_unit:
            # Only change value if it's different
            price_unit = self.price_unit
            self.price_unit = price
        price = super(PurchaseOrderLine, self)._get_stock_move_price_unit()
        if price_unit:
            self.price_unit = price_unit
        return price
