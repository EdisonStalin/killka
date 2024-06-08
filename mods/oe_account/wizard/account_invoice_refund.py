# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Credit Note
    'in_refund': 'in_invoice',          # Vendor Credit Note
}

CODE2REFUND = {
    'out_invoice': '18',        # Customer Invoice
    'in_invoice': '01',          # Vendor Bill
    'out_refund': '04',        # Customer Credit Note
    'in_refund': '04',          # Vendor Credit Note
}

class AccountInvoiceRefund(models.TransientModel):

    _inherit = "account.invoice.refund"
    
    @api.model
    def _get_invoice(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.id
        return False


    @api.model
    def _get_type_invoice(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return TYPE2REFUND[inv.type]
        return False


    @api.model
    def _get_authorization(self):
        context = dict(self._context or {})
        res = {'domain': {}, 'values': {}}
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            domain = [('is_electronic', '=', inv.is_electronic), ('type_document_id.code', '=', '04')]
            if TYPE2REFUND[inv.type] == 'out_refund':
                domain += [('partner_id', '=', inv.company_id.partner_id.id), ('type', '=', 'internal')]
            else:
                domain += [('partner_id', '=', inv.partner_id.id), ('type', '=', 'external')]
            auth = self.env['account.authorization'].search(domain, limit=1)
            if auth: res['values']['authorization_id'] = auth.id
            res['domain'] = {'authorization_id': domain}
        return res
    
    
    invoice_id = fields.Many2one('account.invoice', 'Origin invoice', default=_get_invoice)
    partner_id = fields.Many2one('res.partner', string='Partner', related='invoice_id.partner_id', readonly=True, related_sudo=False)
    tax_support_id = fields.Many2one('account.tax.support', string='Tax Support', domain=[('active', '=', True)], track_visibility='always')
    type_document_id = fields.Many2one('account.type.document', string='Voucher type', required=True, domain=[('active', '=', True)], track_visibility='always')
    authorization_id = fields.Many2one('account.authorization', string='Authorization', default=_get_authorization)
    number = fields.Char(string='Number', size=9, default='000000000')
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
    ], string='Type', default=_get_type_invoice)


    @api.model
    def default_get(self, default_fields):
        res = super(AccountInvoiceRefund, self).default_get(default_fields)
        if res.get('type', False) and not res.get('type_document_id', False):
            res['tax_support_id'] = self.env.ref('oe_account.data_account_tax_support_01').id
        if res.get('type', False) and not res.get('type_document_id', False):
            res['type_document_id'] = self.env.ref('oe_account.data_type_documente_04').id
        return res
        

    @api.onchange('filter_refund')
    def onchange_filter_refund(self):
        res = {'domain': {}}
        domain = []
        inv_id = self._context.get('active_id', False)
        domain += [('type', '=', 'out' if self.type == 'out_refund' else 'in')]
        if inv_id:
            invoice_id = self.env['account.invoice'].browse(inv_id)
            type_ref = 'internal' if invoice_id.type in ['out_invoice'] else 'external'
            domain += [('company_id', '=', invoice_id.company_id.id), ('partner_id', '=', invoice_id.partner_id.id), ('type', '=', type_ref)]
            if self.type_document_id: domain += [('type_document_id.code', '=', self.type_document_id.code)]
            res['domain']['authorization_id'] = domain
        return res


    @api.onchange('type_document_id')
    def onchange_is_electronic(self):
        res = {'domain': {}, 'values': {}}
        domain = [('company_id', '=', self.env.user.company_id.id)]
        if self.type == 'in_refund': domain = [('partner_id', '=',  self.invoice_id.partner_id.id)]
        if self.type_document_id.id: domain += [('type_document_id', '=', self.type_document_id.id)]
        if self.type in ['out_invoice', 'out_refund']: domain += [('type', '=', 'internal')]
        domain += [('is_electronic', '=', self.invoice_id.is_electronic)]
        auth = self.env['account.authorization'].search(domain, limit=1, order="id asc")
        if not self.authorization_id or self.authorization_id != auth: 
            self.authorization_id = auth.id
        res['domain'] = {'authorization_id': domain}
        return res


    @api.multi
    def compute_refund(self, mode='refund'):
        inv_obj = self.env['account.invoice']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        xml_id = False

        for form in self:
            created_inv = []
            date = False
            description = False
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'cancel']:
                    raise UserError(_('Cannot create credit note for the draft/cancelled invoice.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_('Cannot create a credit note for the invoice which is already reconciled, invoice should be unreconciled first, then only you can add credit note for this invoice.'))

                date = form.date or False
                description = form.description or inv.name
                refund = inv.refund(form.date_invoice, date, description, inv.journal_id.id, form)

                created_inv.append(refund.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    refund.action_invoice_open()
                    for tmpline in refund.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                        invoice = invoice[0]
                        o_invoice_id = invoice['id']
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id,
                            'refund_invoice_id': o_invoice_id,
                            'number': '%%0%sd' % 9 % 0,
                        })
                        for field in inv_obj._get_refund_common_fields():
                            if inv_obj._fields[field].type == 'many2one':
                                invoice[field] = invoice[field] and invoice[field][0]
                            else:
                                invoice[field] = invoice[field] or False
                        inv_refund = inv_obj.create(invoice)
                        created_inv.append(inv_refund.id)
                xml_id = inv.type == 'out_invoice' and 'action_invoice_out_refund' or \
                         inv.type == 'out_refund' and 'action_invoice_tree1' or \
                         inv.type == 'in_invoice' and 'action_invoice_in_refund' or \
                         inv.type == 'in_refund' and 'action_invoice_tree2'
                # Put the reason in the chatter
                subject = _("Credit Note")
                body = description
                refund.message_post(body=body, subject=subject)
        if xml_id:
            result = self.env.ref('account.%s' % (xml_id)).read()[0]
            invoice_domain = safe_eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result
        return True


    def invoice_refund(self):
        data = self.read(['filter_refund', 'number', 'authorization_id', 'type_document_id', 'tax_support_id'])[0]
        return self.compute_refund(data)


