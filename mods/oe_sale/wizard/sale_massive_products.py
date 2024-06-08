# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp

MAP_PURCHASE_TYPE = {
    'sale': 'sale.order.line',
    'delivery': 'sale.order.line',
}


class SaleMassiveProducts(models.TransientModel):
    _name = "sale.massive.products"
    _description = "Add of massive products"
    

    categ_id = fields.Many2one('product.category', string='Category', help="Select category for the current product")
    line_products = fields.Many2many('product.product', 'sale_massive_products_rel', 'massive_id', 'product_id', string='Products')
    type_request = fields.Selection(selection=[('sale', 'Sale'), ('delivery', 'Delivery'),], 
                                     string='Type', default='sale', required=True)
    product_qty = fields.Float(string='Quantity', default=1.0, digits=dp.get_precision('Product Unit of Measure'))
    price_unit = fields.Float(string='Unit Price', digits=dp.get_precision('Product Price'))
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    
    def _get_line(self, record_id, product):
        price_unit = product._get_cost()
        vals = {
            'product_id': product.id,
            'name': product.name,
            'product_uom': product.uom_po_id.id,
            'product_uom_qty': self.product_qty,
            'price_unit': price_unit,
            'order_id': record_id,
            'tax_id': [(6 , 0, self.taxes_id.ids)],
        }
        return vals
    

    def _action_execute(self, vals, model):
        new_record_id = self.env[model].create(vals)
        new_record_id._compute_amount()


    @api.multi
    def add_products(self):
        record_id = self._context.get('active_id')
        model = MAP_PURCHASE_TYPE.get(self.type_request, False)
        for product in self.line_products:
            vals = self._get_line(record_id, product)
            self._action_execute(vals, model)
        return {'type': 'ir.actions.act_window_close'}  
                
                
