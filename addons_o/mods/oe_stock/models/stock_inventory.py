# -*- coding: utf-8 -*-

import binascii
import logging
import tempfile

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

class Inventory(models.Model):
    _inherit = 'stock.inventory'
    
    barcode = fields.Char(string='Barcode', help='Point to execute the barcode reading and register the product in the list.')
    file = fields.Binary(string='File', attachment=True)
    filename = fields.Char('Filename', size=250)

    @api.model
    def _selection_filter(self):
        """ Get the list of filter allowed according to the options checked
        in 'Settings\Warehouse'. """
        res_filter = super(Inventory, self)._selection_filter()
        res_filter += [('file', _('File'))]
        return res_filter

    def _add_product(self, product_id):
        list_barcode = list(set(self.line_ids.mapped('barcode')))
        if self.barcode in list_barcode:
            for line in self.line_ids:
                if line.product_id.barcode == self.barcode:
                    line.qty += 1
                    break
        else:
            vals = {
                'product_id': product_id.id,
                'product_uom_id': product_id.uom_id.id,
                'description': product_id.name,
                'product_qty': 1,
                'location_id': self.location_id.id,
            }
            new_line = self.env['stock.inventory.line'].new(vals)
            self.line_ids += new_line


    @api.onchange('barcode')
    def _onchange_barcode_scanning(self):
        if not self.barcode:
            self.barcode = None
            return False
        product_id = self.env['product.product'].search([('barcode', '=', self.barcode)], limit=1)
        if self.barcode and not product_id:
            self.barcode = None
            raise UserError(_('No product is available for this barcode.'))
        list_barcode = list(set(self.line_ids.mapped('barcode')))
        if self.barcode in list_barcode:
            for line in self.line_ids:
                if line.product_id.barcode == self.barcode:
                    line.product_qty += 1
                    break
        elif product_id:
            self._add_product(product_id)
        self.barcode = None

    def action_start(self):
        if self.filter=='file': self.exhausted=True
        return super(Inventory, self).action_start()

    def _get_inventory_lines_values(self):
        if self.filter=='file':
            vals = []
            Product = self.env['product.product']
            # Empty recordset of products available in stock_quants
            quant_products = self.env['product.product']
            # Empty recordset of products to filter
            products_to_filter = self.env['product.product']
            file_values = self.import_xls()
            locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
            domain = ' location_id in %s AND active = TRUE'
            args = (tuple(locations.ids),)
            if len(file_values):
                domain += ' AND product_id in %s'
                args += (tuple(file_values.keys()),)
                products_to_filter |= Product.browse(file_values.keys())
            
            self.env.cr.execute("""SELECT product_id, sum(quantity) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
                FROM stock_quant
                LEFT JOIN product_product
                ON product_product.id = stock_quant.product_id
                WHERE %s
                GROUP BY product_id, location_id, lot_id, package_id, partner_id """ % domain, args)
    
            for product_data in self.env.cr.dictfetchall():
                # replace the None the dictionary by False, because falsy values are tested later on
                for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                    product_data[void_field] = False
                product_data['theoretical_qty'] = product_data['product_qty']
                if product_data['product_id']:
                    product_data['product_uom_id'] = file_values[product_data['product_id']]['product_uom_id']
                    quant_products |= Product.browse(product_data['product_id'])
                vals.append(product_data)
            if self.exhausted:
                exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
                vals.extend(exhausted_vals)
            for line in vals:
                line.update(file_values[line['product_id']])
            return vals
        else:
            return super(Inventory, self)._get_inventory_lines_values()

    @api.multi
    def action_done(self):
        for inventory in self:
            for line in inventory.line_ids:
                if not line.prod_lot_id and line.product_id.tracking != 'none':
                    vals = {
                        'name': self.env['ir.sequence'].next_by_code('stock.lot.serial'),
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_id.uom_id.id,
                        'product_qty': line.product_qty,
                    }
                    dates_dict = self.env['stock.production.lot']._get_dates(line.product_id.id)
                    vals.update(dates_dict)
                    prod_lot_id = self.env['stock.production.lot'].create(vals)
                    line.prod_lot_id = prod_lot_id
        return super(Inventory, self).action_done()
    
    @api.multi
    def import_xls(self):
        try:
            fp = tempfile.NamedTemporaryFile(delete= False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
        except Exception:
            raise UserWarning(_("Invalid file!."))
        
        vals = {}
        errors = []
        dict_list = []
        keys = sheet.row_values(0)
        values = [sheet.row_values(i) for i in range(1, sheet.nrows)]
        for value in values:
            dict_list.append(dict(zip(keys, value)))
        obj_lot = self.env['stock.production.lot'].sudo()
        for line in self.web_progress_iter(dict_list, _('recording the amount') + "({})".format(self._description)):
            product_id = self.env['product.product'].sudo().search([('default_code', '=', line.get('product_id'))])
            if not product_id:
                errors += [_('Product %s %s') % (line.get('product_id'), line.get('product_id/name'))]
                continue
            if 'product_id/name' in line and not product_id:
                product_id = self.env['product.product'].sudo().search([('name', '=', line.get('product_id'))])
            if 'prod_lot_id' in line:
                prod_lot_id = obj_lot.search([('name','=',line['prod_lot_id'])])
                if not prod_lot_id and line.get('prod_lot_id', False):
                    prod_lot_id = obj_lot.create({'name': line['prod_lot_id'], 'product_id': product_id.id})
            if product_id.id not in vals:
                vals[product_id.id] = {}
            vals[product_id.id]['prod_lot_id'] = prod_lot_id and prod_lot_id.id or False
            vals[product_id.id]['product_uom_id'] = product_id.uom_id and product_id.uom_id.id or False
            vals[product_id.id]['product_qty'] = float(line.get('product_qty', 0.0))
        if len(errors):
            errors.insert(0, _('Product not located in the system, check for the name or code that is registered:'))
            raise UserError('\n'.join(e for e in errors))
        return vals

class InventoryLine(models.Model):
    _inherit = 'stock.inventory.line'
    
    barcode = fields.Char(related='product_id.barcode')
