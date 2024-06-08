# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, fields, api, _

class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"


    @api.model
    def _get_picking_invoice(self):
        invoice = self.env['account.invoice'].browse(self._context.get('active_id'))
        if invoice.type == 'out_invoice':
            return invoice.picking_transfer_id
        if invoice.type == 'in_invoice':
            return invoice.picking_type_id


    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', default=_get_picking_invoice, readonly=True)


class InvoiceStockMove(models.Model):
    _inherit = 'account.invoice'


    @api.model
    def _default_picking_receive(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        #if self.authorization_id.picking_type_id:
        #    types = self.authorization_id.picking_type_id
        #else:
        types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)], limit=1)
        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        if self.picking_type_id and self.type == 'in_invoice':
            if types != self.picking_type_id :
                types = self.picking_type_id
        return types[:1]


    @api.model
    def _default_picking_transfer(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        #if self.authorization_id.picking_type_id:
        #    types = self.authorization_id.picking_type_id
        #else:
        types = type_obj.search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)], limit=1)
        if not types:
            types = type_obj.search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
        if self.picking_transfer_id and self.type == 'out_invoice':
            if types != self.picking_transfer_id:
                types = self.picking_transfer_id
        return types[:4]


    picking_count = fields.Integer(string="Count")
    invoice_picking_id = fields.Many2one('stock.picking', string="Picking Id")
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', required=True, default=_default_picking_receive,
                                      help="This will determine picking type of incoming shipment")
    picking_transfer_id = fields.Many2one('stock.picking.type', 'Deliver To', default=_default_picking_transfer,
                                          help="This will determine picking type of outgoing shipment")


    @api.model
    def default_get(self,default_fields):
        res = super(InvoiceStockMove, self).default_get(default_fields)
        if self.env.context.get('active_model', '') == 'sale.order':
            sale = self.env['sale.order'].browse(self.env.context.get('active_id'))
            domain = [('partner_id', '=', sale.partner_id.id), ('company_id', '=', sale.company_id.id), ('origin', '=', sale.name)]
            if self._get_install_sale_stock():
                domain.extend([('sale_id', '=', sale.id)])
            stock_picking_id = self.env['stock.picking'].search(domain)
            res['invoice_picking_id'] = stock_picking_id.id
            res['picking_transfer_id'] = stock_picking_id.picking_type_id.id
            res['picking_count'] = len(stock_picking_id)
        return res


    def _get_install_sale_stock(self):
        module_sale_stock = self.sudo().env['ir.module.module'].search([('name', '=', 'sale_stock'), ('state', '=', 'installed')])
        return module_sale_stock and True or False


    @api.onchange('user_id')
    def _onchage_authorization_id(self):
        picking_id = self._default_picking_transfer()
        self.picking_transfer_id = picking_id.id


    @api.multi
    def action_stock_receive(self):
        for order in self:
            if not order.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if not self.number:
                raise UserError(_('Please Validate invoice.'))
            if not self.invoice_picking_id:
                pick = {
                    'picking_type_id': self.picking_type_id.id,
                    'partner_id': self.partner_id.id,
                    'origin': self.number,
                    'location_dest_id': self.picking_type_id.default_location_dest_id.id,
                    'location_id': self.partner_id.property_stock_supplier.id
                }
                picking = self.env['stock.picking'].create(pick)
                self.invoice_picking_id = picking.id
                self.picking_count = len(picking)
                moves = order.invoice_line_ids.filtered(lambda r: r.product_id.type in ['product', 'consu'])._create_stock_moves(picking)
                move_ids = moves._action_confirm()
                move_ids._action_assign()
                for move_line in self.invoice_picking_id.move_lines:
                    move_line.quantity_done = move_line.reserved_availability
                order.invoice_picking_id.button_validate()
                order.env.user.notify_info(_('A movement was made in the inventory successfully.'))


    @api.multi
    def action_stock_transfer(self):
        for order in self:
            if not order.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if not self.number:
                raise UserError(_('Please Validate invoice.'))
            if not self.invoice_picking_id:
                pick = {
                    'picking_type_id': self.picking_transfer_id.id,
                    'partner_id': self.partner_id.id,
                    'origin': self.number,
                    'location_dest_id': self.partner_id.property_stock_customer.id,
                    'location_id': self.picking_transfer_id.default_location_src_id.id
                }
                picking = self.env['stock.picking'].create(pick)
                self.invoice_picking_id = picking.id
                self.picking_count = len(picking)
                moves = order.invoice_line_ids.filtered(lambda r: r.product_id.type in ['product', 'consu'])._create_stock_moves_transfer(picking)
                move_ids = moves._action_confirm()
                move_ids._action_assign()
                for move_line in self.invoice_picking_id.move_lines:
                    move_line.quantity_done = move_line.reserved_availability
                order.invoice_picking_id.button_validate()
                order.env.user.notify_info(_('A movement was made in the inventory successfully.'))


    @api.multi
    def action_stock_back(self):
        for order in self:
            if not order.refund_invoice_id:
                inv_name = '%s-%s-%s' % (order.tmpl_entity, order.tmpl_emission, order.tmpl_number)
                inv_origin = self.search([('name', '=', inv_name), ('partner_id', '=', order.partner_id.id)])
            else:
                inv_origin = order.refund_invoice_id
            if not order.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if not inv_origin:
                raise UserError(_('Please Validate invoice.'))
            picking_id = inv_origin.invoice_picking_id
            res = self._get_wizard_(picking_id)
            for line in order.invoice_line_ids:
                for rline in res.get('product_return_moves', []):
                    if rline[2]['product_id'] == line.product_id.id:
                        rline[2]['quantity'] = line.quantity
            wizard_picking_id = self.with_context(active_id=picking_id.id).env['stock.return.picking'].create(res)
            new_picking_id, pick_type_id = wizard_picking_id._create_returns()
            order.invoice_picking_id = new_picking_id
            self.picking_count = len(order.invoice_picking_id)
            for move_line in self.invoice_picking_id.move_lines:
                move_line.quantity_done = move_line.reserved_availability
            order.invoice_picking_id.button_validate()
            order.env.user.notify_info(_('A movement was made in the inventory successfully.'))


    def _get_wizard_(self, picking):
        fields = ['move_dest_exists', 'product_return_moves', 'parent_location_id', 'original_location_id', 'location_id']
        res = self.with_context(active_id=picking.id).env['stock.return.picking'].default_get(fields)
        return res


    @api.multi
    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_ready')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        result['domain'] = [('id', '=', self.invoice_picking_id.id)]
        pick_ids = sum([self.invoice_picking_id.id])
        if pick_ids:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids or False
        return result


class SupplierInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'


    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            price_unit = line.price_unit
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.uom_id.id,
                'location_id': line.invoice_id.partner_id.property_stock_supplier.id,
                'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
                'picking_id': picking.id,
                'move_dest_id': False,
                'state': 'draft',
                'company_id': line.invoice_id.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': picking.picking_type_id.id,
                'procurement_id': False,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            }
            diff_quantity = line.quantity
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += moves.create(template)
        return done


    def _create_stock_moves_transfer(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            price_unit = line.price_unit
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.uom_id.id,
                'location_id': picking.picking_type_id.default_location_src_id.id,
                'location_dest_id': line.invoice_id.partner_id.property_stock_customer.id,
                'picking_id': picking.id,
                'move_dest_id': False,
                'state': 'draft',
                'company_id': line.invoice_id.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': picking.picking_type_id.id,
                'procurement_id': False,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            }
            diff_quantity = line.quantity
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += moves.create(template)
        return done
