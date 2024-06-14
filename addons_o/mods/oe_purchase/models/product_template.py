# -*- coding: utf-8 -*-

from odoo import models, api, fields

class ProductPriceHistory(models.Model):
    """ Keep track of the ``product.template`` standard prices as they are changed. """
    _inherit = 'product.price.history'

    order_id = fields.Many2one('purchase.order', string='Purchase Order')


class ProductTemplate(models.Model):
    _inherit = 'product.template'


    @api.depends('history_price_ids')
    def _get_last_cost(self):
        obj_product = self.env['product.product']
        for prod in self:
            product_id = obj_product.search([('product_tmpl_id', '=', prod.id)])
            prod.last_cost = product_id.get_history_price(self.env.user.company_id.id, date=None, order=True)


class ProductProduct(models.Model):
    _inherit = 'product.product'


    @api.depends('history_price_ids')
    def _get_last_cost(self):
        for product_id in self:
            product_id.last_cost = product_id.get_history_price(self.env.user.company_id.id, date=None, order=True)


    @api.multi
    def _set_standard_price(self, value, order_id=False):
        ''' Store the standard price change in order to be able to retrieve the cost of a product for a given date'''
        PriceHistory = self.env['product.price.history']
        for product in self:
            PriceHistory.create({
                'product_id': product.id,
                'cost': value,
                'company_id': self._context.get('force_company', self.env.user.company_id.id),
                'order_id': order_id and order_id.id or False,
            })


    @api.multi
    def get_history_price(self, company_id, date=None, order=False):
        domain = [
            ('company_id', '=', company_id),
            ('product_id', 'in', self.ids),
            ('datetime', '<=', date or fields.Datetime.now())]
        if order:
            domain += [('order_id','!=',False)]
        history = self.env['product.price.history'].search(domain, order='datetime desc,id desc', limit=1)
        return history.cost or 0.0
