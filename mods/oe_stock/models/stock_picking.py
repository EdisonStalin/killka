# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Picking(models.Model):
    _inherit = 'stock.picking'
    
    action_type = fields.Selection(selection=[('stock','Stock')], string='Movement Type', default='stock')
    barcode = fields.Char(string='Barcode', help='Point to execute the barcode reading and register the product in the list.')
    guide_reference = fields.Char(string='Guide reference', size=50, copy=False)
    
    def _add_product(self, product_id):
        vals = {
            'product_id': product_id.id,
            'name': product_id.name,
            'date_expected': fields.Date.context_today(self),
            'product_uom': product_id.uom_id.id,
            #'description': product_id.name,
            'product_uom_qty': 1,
            'picking_type_id': self.picking_type_id.id,
            'warehouse_id': self.picking_type_id.warehouse_id.id,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'is_locked': False,
            'origin': self.origin,
            'company_id': self.company_id.id,
            #'move_type': 'direct',
            'location_id': self.location_id and self.location_id.id or False,
            'location_dest_id': self.location_dest_id and self.location_dest_id.id or False,
            #'picking_id': self.id,
        }
            #new_line = self.env['stock.move'].new(vals)
            #self.write({'move_lines': [(0, 0,vals)]})
            #new_line = self.env['stock.move'].create(vals)
            #self.move_lines += new_line
        return [(0, 0, vals)]


    @api.onchange('barcode')
    def _onchange_barcode_scanning(self):
        res = {'value': {}}
        warning = {}
        if not self.barcode:
            self.barcode = None
            return False
        product_id = self.env['product.product'].search([('barcode', '=', self.barcode)], limit=1)
        if self.barcode and not product_id:
            warning = {
                'title': _("Warning for %s") % self.barcode,
                'message': _('No product is available for this barcode.')
            }
            self.barcode = None
        list_barcode = list(set(self.move_lines.filtered(lambda l: l.barcode).mapped('barcode')))
        if self.barcode in list_barcode:
            for line in self.move_lines:
                if line.product_id.barcode == self.barcode:
                    if self.state == 'draft':
                        line.product_uom_qty += 1
                        #line.quantity_done += 1
                        #for move_line in line.move_line_ids.filtered(lambda l: l.product_id == line.product_id):
                        #    move_line.qty_done += 1
                    self.barcode = None
                    break
        else:
            if product_id and self.state == 'draft':
                res['value']['move_lines'] = self._add_product(product_id)
        self.barcode = None
        if warning:
            res['warning'] = warning
        return res
