# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

MAP_PURCHASE_TYPE = {
    'order': 'purchase.order.line',
    'requisition': 'purchase.requisition.line',
}

class PurchaseMassiveProducts(models.TransientModel):
    _name = "purchase.massive.products"
    _description = "Add of massive products"
    

    categ_id = fields.Many2one('product.category', string='Category', help="Select category for the current product")
    line_products = fields.Many2many('product.product', 'purchase_massive_products_rel', 'massive_id', 'product_id', string='Products')
    type_request = fields.Selection(selection=[('requisition', 'Purchase Requisition'),
        ('order', 'Purchase Order'),], string='Type', default='order', required=True)
    product_qty = fields.Float(string='Quantity', default=1.0, digits=dp.get_precision('Product Unit of Measure'))
    price_unit = fields.Float(string='Unit Price', digits=dp.get_precision('Product Price'))
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    
    
    def _get_line(self, record_id, product):
        price_unit = self.price_unit or product._get_cost()
        vals = {
            'product_id': product.id,
            'product_qty': self.product_qty,
            'price_unit': price_unit,
            'available_qty': product.qty_available,
        }
        taxes_id = product.supplier_taxes_id + self.taxes_id
        if self.type_request in ['requisition', 'order']:
            if self.type_request == 'requisition':
                vals['requisition_id'] = record_id
            elif self.type_request == 'order':
                vals.update({
                    'order_id': record_id,
                    'name': product.name,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'product_uom': product.uom_po_id and product.uom_po_id.id or product.uom_id.id,
                })
            vals.update({
                'taxes_id': [(6 , 0, taxes_id.ids)],
            })
        return vals
    

    def _action_execute(self, vals, model):
        new_record_id = self.env[model].create(vals)
        if self.type_request in ['requisition']:
            new_record_id._onchange_product_id()
        if self.type_request in ['order']:
            new_record_id._compute_amount()


    @api.multi
    def add_products(self):
        record_id = self._context.get('active_id')
        model = MAP_PURCHASE_TYPE.get(self.type_request, False)
        for product in self.line_products:
            vals = self._get_line(record_id, product)
            self._action_execute(vals, model)
        return {'type': 'ir.actions.act_window_close'}  
                
                
