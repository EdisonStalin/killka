# -*- coding: utf-8 -*-

import logging

from odoo import models, api

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    @api.multi
    def create_mrp_from_pos(self, products):
        product_ids = []
        if not products:
            return False
        try:
            for product in products:
                flag = 1
                if product_ids:
                    for product_id in product_ids:
                        if product_id['id'] == product['id']:
                            product_id['qty'] += product['qty']
                            flag = 0
                if flag:
                    product_ids.append(product)
            for prod in product_ids:
                if prod['qty'] > 0:
                    product = self.env['product.product'].search([('id', '=', prod['id'])])
                    product_temp = prod['product_tmpl_id'] if 'product_tmpl_id' in prod else product.product_tmpl_id.id
                    bom_count = self.env['mrp.bom'].search([('product_tmpl_id', '=', product_temp)])
                    if bom_count:
                        bom_temp = self.env['mrp.bom'].search([('product_tmpl_id', '=', product_temp),
                                                               ('product_id', '=', False)])
                        bom_prod = self.env['mrp.bom'].search([('product_id', '=', prod['id'])])
                        if bom_prod:
                            bom = bom_prod[0]
                        elif bom_temp:
                            bom = bom_temp[0]
                        else:
                            bom = []
                        if bom:
                            vals = {
                                'origin': 'POS-' + prod['pos_reference'],
                                'state': 'confirmed',
                                'product_id': prod['id'],
                                'product_tmpl_id': product_temp,
                                'product_uom_id': prod['uom_id'],
                                'product_qty': prod['qty'],
                                'bom_id': bom.id,
                            }
                            new_mrp = self.sudo().create(vals)
                            if 'pos_reference' in prod:
                                order_id = self.env['pos.order'].search([('pos_reference', '=', prod['pos_reference'])])
                                line_ids = order_id.lines.filtered(lambda x: x.product_id.id == product.id)
                                line_ids.write({'mrp_production_id': new_mrp.id})
                            vals_validate = {'production_id': new_mrp.id, 'product_qty': new_mrp.product_qty}
                            new_mrp._cr.commit()
                            new_mrp._execute_mrp(vals_validate)
        except Exception as e:
            _logger.error('Order MRP %s', e)
        return True


    def _execute_mrp(self, vals):        
        self.action_assign()
        new_mrp_wizard = self.env['mrp.product.produce'].create(vals)
        new_mrp_wizard.do_produce()
        if self.state == 'progress':
            self.button_mark_done()
        return True
