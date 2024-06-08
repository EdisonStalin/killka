# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp

class ProductCategory(models.Model):
    _inherit = 'product.category'

    not_entry_in = fields.Boolean(string='Not Entry In', help='Do not register entry accounting movement')

class ProductProduct(models.Model):
    _inherit = "product.product"


    @api.depends('standard_price', 'history_price_ids.cost', 'qty_available')
    def _compute_product_price(self):
        super(ProductProduct, self)._compute_product_price()
        for prod in self:
            candidates = prod._get_fifo_candidates_in_move()
            remaining_value = sum([0]+ candidates.mapped('remaining_value'))
            prod._compute_product_price = remaining_value/prod.qty_available if prod.qty_available > 0.0 else 0.0


    avarage_cost = fields.Float('Current Average Cost', compute="_compute_product_price", store=True,
        digits=dp.get_precision('Product Price'), help='Current Stock Average Cost')

    def _get_cost(self):
        price_unit = 0.0
        if self.case_method == 'average':
            price_unit = self.avarage_cost
        elif self.case_method == 'last_cost':
            price_unit = self.last_cost
        else:
            price_unit = self.standard_price
        if price_unit == 0.0 and self.case_method == 'average':
            price_unit = self.last_cost
            if price_unit == 0.0:
                price_unit = self.standard_price
        if price_unit == 0.0 and self.case_method == 'last_cost':
            price_unit = self.standard_price
        return price_unit

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('product_variant_ids', 'product_variant_ids.standard_price',
                 'history_price_ids', 'history_price_ids.cost')
    def _compute_standard_price(self):
        dic = {}
        super(ProductTemplate, self)._compute_standard_price()
        obj_order_line = self.env['purchase.order.line']
        products = self.env['product.product'].search([('product_tmpl_id','in',self.ids)])
        for prod in products:
            domain = [('product_id','=',prod.id),('company_id','=',self.env.user.company_id.id),('state', 'in', ['purchase','done'])]
            order_line_ids = obj_order_line.search(domain)
            if prod.product_tmpl_id.id not in dic:
                dic[prod.product_tmpl_id.id] = {'cost':0.0, 'count':0}
            for line in order_line_ids:
                dic[prod.product_tmpl_id.id]['cost'] += line.price_subtotal
                dic[prod.product_tmpl_id.id]['count'] += line.product_qty
        for record in self:
            average_cost = 0.0
            if record.id in dic:
                average_cost = dic[record.id]['cost'] / dic[record.id]['count'] if dic[record.id]['count'] else 0.0
            record.avarage_cost = average_cost

    avarage_cost = fields.Float('Current Average Cost', compute="_compute_standard_price", store=True, digits=dp.get_precision('Product Price'))
