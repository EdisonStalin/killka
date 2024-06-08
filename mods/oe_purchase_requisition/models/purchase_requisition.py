# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_round
import odoo.addons.decimal_precision as dp

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    @api.depends('line_ids.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id.id)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'


    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            price_unit = line._get_discounted_price_unit()
            taxes = line.taxes_id.compute_all(price_unit, line.requisition_id.currency_id, line.product_qty, product=line.product_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })


    available_qty = fields.Float(string='Available Qty', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    last_cost = fields.Float(string='Last Cost', digits=dp.get_precision('Product Price'), default=0.0, help='Current Last Cost')
    type_discount = fields.Selection(default='percent', required=True, selection=[('fixed', 'Fixed'), ('percent', 'Percentage')])
    discount = fields.Float(string='Discount', digits=dp.get_precision('Discount'))
    currency_id = fields.Many2one(related='requisition_id.currency_id', store=True, string='Currency', readonly=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)


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


    @api.onchange('product_id')
    def _onchange_product_id(self):
        super(PurchaseRequisitionLine, self)._onchange_product_id()
        if self.product_id:
            self.available_qty = self.product_id.qty_available or 0.0
            self.last_cost = self.product_id.last_cost
