# -*- coding: utf-8 -*-

import logging
import psycopg2

from odoo import models, api, fields, tools, _
from odoo.addons import decimal_precision as dp
from odoo.tools import float_round
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'


    @api.depends('details_tax', 'statement_ids', 'lines.price_subtotal_incl', 'lines.discount')
    def _compute_amount_all(self):
        prec = self.env['decimal.precision'].precision_get('Account')
        for order in self:
            order.amount_paid = order.amount_return = order.amount_tax = 0.0
            order.amount_paid = sum(payment.amount for payment in order.statement_ids)
            order.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in order.statement_ids)
            order.subtotal = sum(line.price_subtotal for line in order.lines)
            order.amount_discount = sum((line.price_subtotal*line.discount)/100 for line in order.lines)
            order.amount_base_tax = sum(line.price_subtotal for line in order.lines if line.price_tax != 0.0)
            order.amount_tax = sum(self._amount_line_tax(line, order.fiscal_position_id) for line in order.lines)
            amount_untaxed = float_round(sum(line.price_subtotal for line in order.lines), precision_digits=prec)
            order.amount_total = order.amount_tax + amount_untaxed


    access_key = fields.Char(string='Access key', related='invoice_id.access_key', store=True, copy=False)
    details_tax = fields.Boolean('Details Tax', copy=False)
    to_invoice = fields.Boolean('Create Invoice', copy=False)
    subtotal = fields.Float(string='Subtotal without tax', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount_all')
    amount_discount = fields.Float(string='Discount', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount_all')
    amount_base_tax = fields.Float(string='Tax difference of 0%', store=True, readonly=True, compute='_compute_amount_all')
    amount_tax = fields.Float(compute='_compute_amount_all', string='Taxes', digits=dp.get_precision('Account Total'), store=True)
    amount_total = fields.Float(compute='_compute_amount_all', string='Total', digits=dp.get_precision('Account Total'), store=True)
    amount_paid = fields.Float(compute='_compute_amount_all', string='Paid', states={'draft': [('readonly', False)]}, 
                               readonly=True, digits=dp.get_precision('Account Total'), store=True)
    amount_return = fields.Float(compute='_compute_amount_all', string='Returned', digits=dp.get_precision('Account Total'), store=True)
    return_ref = fields.Char(string='Return Ref', readonly=True, copy=False)
    return_status = fields.Selection([
        ('nothing_return', 'Nothing Returned'),
        ('partialy_return', 'Partialy Returned'),
        ('fully_return', 'Fully Returned')], string="Return Status", default='nothing_return', 
        readonly=True, copy=False, help="Return status of Order")
    refund_move = fields.Many2one('account.move', string='Refund Journal Entry', readonly=True, copy=False)
    pos_reference = fields.Char(string='Receipt Ref', readonly=False, copy=False)


    @api.model
    def default_get(self, default_fields):
        res = super(PosOrder, self).default_get(default_fields)
        if 'pricelist_id' not in res or not res.get('pricelist_id', False):
            res['pricelist_id'] = self._default_pricelist().id
        return res

    def _action_approved_invoice(self, invoice_ids):
        i = 0
        max_pos = len(invoice_ids)
        for invoice in invoice_ids:
            i += 1
            invoice.action_invoice_open()
            invoice._cr.commit()
            _logger.info(_('Invoice %s %s of %s') % (invoice.name, i, max_pos))

    @api.multi
    def action_approved_invoice(self):
        invoices = self.mapped('invoice_id').filtered(lambda i: i.state=='draft')
        self._action_approved_invoice(invoices)

    @api.model
    def generate_document(self):
        i = 0
        pos_ids = self.search([('to_invoice', '=', True),('state','in',['paid','done'])], limit=30, order='id ASC')
        max_pos = len(pos_ids)
        for pos in pos_ids:
            i += 1
            pos.action_pos_order_invoice()
            pos._cr.commit()
            _logger.info(_('Order %s %s of %s') % (pos.name, i, max_pos))
        
        invoice_ids = self.env['account.invoice'].search([('state', 'in', ['draft'])], limit=30, order='id ASC')
        self._action_approved_invoice(invoice_ids)
        _logger.info(_('Successfully completed the process'))


    @api.model
    def get_lines(self, ref):
        result = []
        order_id = self.search([('pos_reference', '=', ref)], limit=1)
        if order_id:
            lines = self.env['pos.order.line'].search([('order_id', '=', order_id.id)])
            for line in lines:
                if line.qty - line.returned_qty > 0:
                    new_vals = {
                        'product_id': line.product_id.id,
                        'product': line.product_id.name,
                        'qty': line.qty - line.returned_qty,
                        'price_unit': line.price_unit,
                        'discount': line.discount,
                        'line_id': line.id,
                    }
                    result.append(new_vals)
        return [result]

    @api.model
    def create_from_ui(self, orders):
        # Keep only new orders
        submitted_references = [o['data']['name'] for o in orders]
        pos_order = self.search([('pos_reference', 'in', submitted_references)])
        existing_orders = pos_order.read(['pos_reference'])
        existing_references = set([o['pos_reference'] for o in existing_orders])
        orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]
        order_ids = []

        for tmp_order in orders_to_save:
            to_invoice = tmp_order['to_invoice'] or tmp_order['data'].get('to_invoice')
            order = tmp_order['data']
            if to_invoice:
                self._match_payment_to_invoice(order)
            pos_order = self._process_order(order)
            order_ids.append(pos_order.id)

            try:
                pos_order.action_pos_order_paid()
            except psycopg2.DatabaseError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))
            if pos_order.picking_id:
                pos_order.write({'state': 'paid'})
            _logger.info('Orden %s -> %s' % (pos_order.name, pos_order.state))
        return order_ids


    def _action_create_invoice_line(self, line=False, invoice_id=False):
        invoice_line = self.env['account.invoice.line']
        inv_name = line.product_id.name_get()[0][1]
        inv_line = {
            'invoice_id': invoice_id,
            'product_id': line.product_id.id,
            'quantity': abs(line.qty),
            'account_analytic_id': self._prepare_analytic_account(line),
            'name': inv_name,
        }
        # Oldlin trick
        invoice_line = invoice_line.new(inv_line)
        invoice_line._onchange_product_id()
        invoice_line.invoice_line_tax_ids = invoice_line.invoice_line_tax_ids.filtered(lambda t: t.company_id.id == line.order_id.company_id.id).ids
        fiscal_position_id = line.order_id.fiscal_position_id
        if fiscal_position_id:
            invoice_line.invoice_line_tax_ids = fiscal_position_id.map_tax(invoice_line.invoice_line_tax_ids, line.product_id, line.order_id.partner_id)
        invoice_line.invoice_line_tax_ids = invoice_line.invoice_line_tax_ids.ids
        # We convert a new id object back to a dictionary to write to
        # bridge between old and new api
        #invoice_line.onchange_form_code_ids()
        inv_line = invoice_line._convert_to_write({name: invoice_line[name] for name in invoice_line._cache})
        inv_line.update(price_unit=line.price_unit, discount=line.discount, name=inv_name)
        return invoice_line.create(inv_line)


    def _generate_document(self, order, refund=False):
        obj_invoice = self.env['account.invoice']
        local_context = dict(self.env.context, force_company=order.company_id.id, company_id=order.company_id.id)
        
        document = obj_invoice.new(order._prepare_invoice(refund))
        document._onchange_partner_id()
        document.fiscal_position_id = order.fiscal_position_id
        
        doc = document._convert_to_write({name: document[name] for name in document._cache})
        new_document = obj_invoice.with_context(local_context).create(doc)
        message = _("This invoice has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (order.id, order.name)
        new_document.message_post(body=message)
        return new_document


    def _order_fields(self, ui_order):
        order = super(PosOrder, self)._order_fields(ui_order)
        order['to_invoice'] = ui_order['to_invoice']
        if 'return_ref' in ui_order.keys() and ui_order['return_ref']:
            order['return_ref'] = ui_order['return_ref']
            parent_order = self.search([('pos_reference', '=', ui_order['return_ref'])], limit=1)
            updated_lines = ui_order['lines']
            ret = 0
            qty = 0
            for uptd in updated_lines:
                if 'line_id' in uptd[2]:
                    domain = [('order_id', '=', parent_order.id), ('id', '=', uptd[2]['line_id'])]
                    line = self.env['pos.order.line'].search(domain, limit=1)
                    if line:
                        line.returned_qty += -(uptd[2]['qty'])
            for line in parent_order.lines:
                qty += line.qty
                ret += line.returned_qty
            if qty-ret == 0:
                if parent_order:
                    parent_order.return_status = 'fully_return'
            elif ret:
                if qty > ret:
                    if parent_order:
                        parent_order.return_status = 'partialy_return'
        return order


    def _prepare_invoice(self, refund):
        """
        Prepare the dict of values to create the new invoice for a pos order.
        """
        try:
            order_id = self
            if not refund:
                invoice_type = 'out_invoice'
                authorization_id = self.session_id.authorization_id
            else:
                invoice_type = 'out_refund'
                authorization_id = self.session_id.refund_authorization_id
                if self.return_ref:
                    order_id = self.search([('pos_reference', '=', self.return_ref)])
            invoice = order_id.invoice_id
            if len(order_id.statement_ids) >= 1:
                method_id = order_id.statement_ids[0].journal_id.method_id
            else:
                method_id = self.env.ref('oe_account.payment_method_20')
            vals = {
                'name': self.name,
                'origin': self.name,
                'account_id': self.partner_id.property_account_receivable_id.id,
                'journal_id': self.session_id.config_id.invoice_journal_id.id,
                'company_id': self.company_id.id,
                'type': invoice_type,
                'reference': self.name,
                'partner_id': self.partner_id.id,
                'comment': self.note or '',
                # considering partner's sale pricelist's currency
                'currency_id': self.pricelist_id.currency_id.id,
                'user_id': self.user_id.id,
                'authorization_id': authorization_id.id,
                'line_info_ids': self._get_authorization_line(authorization_id),
                'type_document_id': authorization_id.type_document_id.id,
                'order_id': order_id.id,
                'method_id': method_id and method_id.id or False,
                #'date_invoice': self.date_order,
            }
            if refund and invoice:
                vals['tmpl_entity'] = invoice.authorization_id.entity
                vals['tmpl_emission'] = invoice.authorization_id.issue
                vals['tmpl_number'] = invoice.number
                vals['tmpl_invoice_date'] = invoice.date_invoice
                vals['origin'] = invoice.name
                vals['type_document_id'] = authorization_id.type_document_id.id if authorization_id.type_document_id else False
                vals['authorization_id'] = authorization_id.id if authorization_id else False
                vals['reason'] = _('Return %s') % invoice.name
                vals['create_order_id'] = self.id
            return vals
        except Exception as ex:
            _logger.error(_('Invoice cannot be generated in order %s %s') % (self.name, ex))

    def _get_authorization_line(self, authorization_id):
        lines_info = []
        for line in authorization_id.line_info_ids:
            lines_info.append((0, 0, {
                'sequence': line.sequence,
                'name': line.name,
                'value_tag': line.value_tag,
            }))
        return lines_info

    def _create_invoice(self):
        self.ensure_one()
        invoices = self.env['account.invoice']
        # Force company for all SUPERUSER_ID action
        check_lines = self.lines.filtered(lambda l: not l.product_id.not_sale).ids
        if not len(check_lines):
            self.write({'to_invoice': False})
            return invoices
        check_invoice = bool(self.lines.filtered(lambda l: l.qty > 0).ids)
        check_refund = bool(self.lines.filtered(lambda l: l.qty < 0).ids)
        local_context = dict(self.env.context, force_company=self.company_id.id, company_id=self.company_id.id)
        if self.invoice_id:
            return self.invoice_id

        if not self.partner_id:
            raise UserError(_('Please provide a partner for the sale.'))
        
        if check_invoice:
            new_invoice = self._generate_document(self)
            self.write({'invoice_id': new_invoice.id, 'state': 'invoiced'})
            for line in self.lines:
                if line.qty >= 0 and not line.product_id.not_sale:
                    self.with_context(local_context)._action_create_invoice_line(line, new_invoice.id)

            new_invoice.with_context(local_context).compute_taxes()
            invoices += new_invoice
        
        if check_refund:
            new_refund = self._generate_document(self, True)
            for line in self.lines:
                if line.qty < 0 and not line.product_id.not_sale:
                    self.with_context(local_context)._action_create_invoice_line(line, new_refund.id)
            new_refund.with_context(local_context).compute_taxes()
            new_refund.with_context(force_company=self.env.user.company_id.id).action_invoice_open()
            self.refund_move = new_refund.move_id
            invoices += new_refund
        
        self.write({'state': 'invoiced'})
        return invoices


    @api.multi
    def action_pos_order_paid(self):
        #if not self.test_paid():
        #    raise UserError(_("Order is not paid."))
        if not self.picking_id:
            self.create_picking()
        if self.picking_id and self.amount_total == self.amount_paid:
            self.write({'state': 'paid'})
        return True


    @api.multi
    def create_picking(self):
        if self.picking_id:
            return True
        res = super(PosOrder, self).create_picking()
        if self.picking_id and self.amount_total == self.amount_paid:
            self.write({'state': 'paid'})
        if self.session_id.state == 'closed':
            self.write({'state': 'done'})
        if self.invoice_id:
            self.write({'state': 'invoiced'})
        return res


    @api.multi
    def action_view_refund(self):
        refunds = self.env['account.invoice'].search([('order_id', '=', self.id), ('type', '=', 'out_refund')])
        if not refunds:
            return {}
        
        return {
            'name': _('Customer Refund'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.invoice_form').id,
            'res_model': 'account.invoice',
            'context': "{'type':'out_refund'}",
            'type': 'ir.actions.act_window',
            'res_id': refunds and refunds.ids[0] or False,
        }


    @api.multi
    def action_view_generate_refund(self):
        refunds = self.env['account.invoice'].search([('create_order_id', '=', self.id), ('type', '=', 'out_refund')])
        if not refunds:
            return {}
        
        return {
            'name': _('Credit Note'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.invoice_form').id,
            'res_model': 'account.invoice',
            'context': "{'type':'out_refund'}",
            'type': 'ir.actions.act_window',
            'res_id': refunds and refunds.ids[0] or False,
        }

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _order_line_fields(self, line, session_id=None):
        account_tax = self.env['account.tax'].sudo()
        ir_default = self.env['ir.default'].sudo()
        company = self.env.user.company_id
        default_sale_tax_id = account_tax.browse(ir_default.get('product.template', 'taxes_id', company_id=company.id) or [])
        if 'product_id' not in line[2]:
            _logger.critical(_('No esta el producto %s') % line[2])
            if line and 'name' not in line[2]:
                session = self.env['pos.session'].browse(session_id).exists() if session_id else None
                if session and session.config_id.sequence_line_id:
                    # set name based on the sequence specified on the config
                    line[2]['name'] = session.config_id.sequence_line_id._next()
                else:
                    # fallback on any pos.order.line sequence
                    line[2]['name'] = self.env['ir.sequence'].next_by_code('pos.order.line')
            line[2]['tax_ids'] = [(6, 0, [x.id for x in default_sale_tax_id])]
            return line
        return super(PosOrderLine, self)._order_line_fields(line, session_id)

    @api.depends('price_unit', 'tax_ids', 'qty', 'discount', 'product_id')
    def _compute_amount_line_all(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id
            tax_ids_after_fiscal_position = fpos.map_tax(line.tax_ids, line.product_id, line.order_id.partner_id) if fpos else line.tax_ids
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_ids_after_fiscal_position.compute_all(price, line.order_id.pricelist_id.currency_id, line.qty, product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_subtotal_incl': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    note = fields.Text()
    price_unit = fields.Float(string='Unit Price', default=0.0, digits=dp.get_precision('Product Price'))
    discount = fields.Float(string='Discount (%)', default=0.0, digits=dp.get_precision('Discount'))
    returned_qty = fields.Float(string='Returned Qty', default=0, readonly=True, digits=dp.get_precision('Product Unit of Measure'))
    price_subtotal = fields.Float(compute='_compute_amount_line_all', digits=dp.get_precision('Account'), string='Subtotal w/o Tax', store=True)
    price_subtotal_incl = fields.Float(compute='_compute_amount_line_all', digits=dp.get_precision('Account'), string='Subtotal', store=True)
    price_tax = fields.Float(compute='_compute_amount_line_all', string='Tax', digits=dp.get_precision('Account'), store=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes', readonly=False)

    
    @api.model
    def create(self, values):
        if 'product_id' not in values:
            _logger.critical(_('Not found product %s') % values)
            product_id = self.env.ref('oe_product.product_product_tip')
            values['product_id'] = product_id and product_id.id or False
        #if values.get('line_id') and values.get('qty') < 0:
        #    del values['line_id']
        if 'qty_available' in values:
            del values['qty_available']
        return super(PosOrderLine, self).create(values)
    