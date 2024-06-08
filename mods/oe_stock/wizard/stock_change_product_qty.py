# -*- coding: utf-8 -*-

from odoo import models, fields, tools, _


class ProductChangeQuantity(models.TransientModel):
    _inherit = 'stock.change.product.qty'
    
    reason = fields.Char(string='Update Reason', size=250, required=True, help='Indicate with a message the reason for updating the product.')


    def change_product_qty(self):
        """ Changes the Product Quantity by making a Physical Inventory. """
        Inventory = self.env['stock.inventory']
        for wizard in self:
            product = wizard.product_id.with_context(location=wizard.location_id.id, lot_id=wizard.lot_id.id)
            line_data = wizard._action_start_line()
            message = _("""Update of products %s, from the previous amount %s
                to the current amount of %s, for the reason of %s""") % (product.display_name, product.qty_available, wizard.new_quantity, wizard.reason)
            product.product_tmpl_id.message_post(body=message)
            product.message_post(body=message)

            if wizard.product_id.id and wizard.lot_id.id:
                inventory_filter = 'none'
            elif wizard.product_id.id:
                inventory_filter = 'product'
            else:
                inventory_filter = 'none'
            inventory = Inventory.create({
                'name': _('INV: %s, %s') % (tools.ustr(wizard.product_id.display_name), wizard.reason),
                'filter': inventory_filter,
                'product_id': wizard.product_id.id,
                'location_id': wizard.location_id.id,
                'lot_id': wizard.lot_id.id,
                'line_ids': [(0, 0, line_data)],
            })
            inventory.action_done()
        return {'type': 'ir.actions.act_window_close'}
    