# -*- encoding: utf-8 -*-

from collections import defaultdict
from functools import partial
import json

from dateutil.relativedelta import relativedelta

from odoo import models, api, fields, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import float_compare, float_is_zero
from odoo.tools.float_utils import float_round as round
from odoo.tools.misc import formatLang


TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Credit Note
    'in_refund': 'in_invoice',          # Vendor Credit Note
}

List_Type_Document = {
    'out_invoice': '18',
    'in_invoice': '01',
    'out_refund': '04',
    'in_refund': '04'
}

TYPEWIHHOLDING = {
    'out_invoice': 'in_withholding',
    'in_invoice': 'out_withholding'
}

List_Alter_Table = [
    'ALTER TABLE "account_invoice" DROP CONSTRAINT IF EXISTS "account_invoice_number_uniq"',
    """UPDATE ir_act_report_xml SET binding_model_id=NULL WHERE report_name='account.report_invoice' AND report_name='account.report_invoice'""",
]

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'


    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount',
                 'tax_line_ids.amount_rounding', 'discount',
                 'currency_id', 'company_id', 'date_invoice', 
                 'withholding_ids.amount', 'details_tax', 'apply_tip')
    def _compute_amount(self):
        # Generate one tax line per tax, however many invoice lines it's applied to
        #tax_grouped = self.get_taxes_values()
        #if len(tax_grouped): self._refresh_lines_taxes(tax_grouped)
        digits = self.env['decimal.precision'].precision_get('Account Total')
        subtotal = 0.0
        amount_discount = 0.0
        amount_total_tax = 0.0
        for line in self.invoice_line_ids:
            subtotal += float('{:.4f}'.format(line.price_subtotal))
            if line.discount > 0.0001:
                adiscount = line.discount if line.type_discount=='fixed' else ((line.quantity * line.price_unit) * line.discount) /100.0
                amount_discount += float('{:.4f}'.format(adiscount))
            amount_total_tax += line.price_tax
        amount_subtotal = round(subtotal, precision_digits=digits)
        subtotal += amount_discount + self.discount
        
        amount_untaxed_0 = sum(line.base for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'iva0')
        amount_no_oject_tax = sum(line.base for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'nobiva')
        amount_no_apply_tax = sum(line.base for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'exiva')
        amount_untaxed = sum(line.base for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'iva')
        amount_tax = sum(line.amount_total for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'iva')
        self.amount_base_ice = sum(line.base for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'ice')
        amount_ice = sum(line.amount_total for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'ice')
        self.amount_base_irbpnr = sum(line.base for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'irbpnr')
        amount_irbpnr = sum(line.amount_total for line in self.tax_line_ids if line.tax_id.tax_group_id.type == 'irbpnr')
        
        self.subtotal = subtotal
        self.amount_no_oject_tax = amount_no_oject_tax
        self.amount_no_apply_tax = amount_no_apply_tax
        self.amount_untaxed_0 = amount_untaxed_0
        self.amount_untaxed = amount_untaxed
        self.amount_discount = amount_discount
        self.amount_tax = amount_tax
        self.amount_ice = amount_ice
        self.amount_irbpnr = amount_irbpnr
        amount_tax = round(amount_tax, precision_digits=digits)
        total_tax = amount_tax + amount_irbpnr

        amount_withhold = sum(line.amount for line in self.withholding_ids\
            .filtered(lambda w: w.withholding_id.document_type=='withhold' and w.withholding_id.state == 'approved'))
        amount_fund = sum(line.amount for line in self.withholding_ids\
            .filtered(lambda w: w.withholding_id.document_type=='fund' and w.withholding_id.state == 'approved'))
        amount_penalty = sum(line.amount for line in self.withholding_ids\
            .filtered(lambda w: w.withholding_id.document_type=='penalty' and w.withholding_id.state == 'approved'))

        self.total_tax = total_tax
        self.amount_withhold = amount_withhold
        self.amount_with = amount_fund
        self.amount_penalty = amount_penalty
        total_tip = (amount_subtotal * self.tip_rate)/100 if self.apply_tip else 0.0
        sum_total = amount_untaxed_0 + amount_untaxed + total_tax + amount_no_oject_tax + amount_no_apply_tax
        amount_total = round(sum_total, precision_digits=digits)
        self.amount_subtotal = amount_subtotal
        self.amount_tax_total = amount_total
        self.total_tip = total_tip
        self.total = amount_total + total_tip
        self.amount_total = amount_total + total_tip - (amount_withhold + amount_fund + amount_penalty)
        
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign
        
        withhol_ids = self.withholding_ids.mapped('withholding_id')
        self.withholding_id = withhol_ids


    @api.depends('state', 'partner_id')
    def _get_refund(self):
        for invoice in self:
            invoice.update({
                'refund_count': len(invoice.refund_invoice_ids.filtered(lambda l: l.type!='refund').ids),
            })


    @api.depends('state', 'authorization_id')
    def _get_sequence_prefix(self):
        for invoice in self:
            name_prefix = '%s-%s-' % (invoice.authorization_id.entity or '000', invoice.authorization_id.issue or '000')
            invoice.sequence_number_next_prefix = name_prefix


    @api.depends('state', 'authorization_id')
    def _get_sequence_number_next(self):
        for invoice in self:
            number = '%%0%sd' % '9' % invoice.internal_number
            invoice.sequence_number_next = number
            invoice.number = number


    @api.depends('state', 'residual')
    def _get_document_count(self):
        for invoice in self:            
            withhold_ids = invoice.withholding_ids.mapped('withholding_id').filtered(lambda w: w.type == TYPEWIHHOLDING[invoice.type] and w.document_type=='withhold')
            invoice.update({
                'withholding_count': len(set(withhold_ids.ids)),
            })

    @api.model
    def _default_document_type(self):
        obj_type_document = self.env['account.type.document']
        if self._context.get('default_type_document_id', False):
            return obj_type_document.browse(self._context.get('default_type_document_id'))
        domain = []
        if self._context.get('default_document_type', False)=='clearance':
            domain += [('code','=','03')]
        else:
            domain += [('code','=',List_Type_Document[self._context.get('type', 'out_invoice')])]
        return obj_type_document.search(domain, limit=1)

    @api.model
    def _default_authorization(self):
        if self._context.get('default_authorization_id', False):
            return self.env['account.authorization'].browse(self._context.get('default_authorization_id'))
        journal = self._default_journal()
        if journal.authorization_id:
            return journal.authorization_id
        inv_type = self._context.get('type', 'out_invoice')
        domain = self._domain_authorization(False, False, True, inv_type)
        return self._get_authorization(domain)

    @api.model
    def _default_tax_support(self):
        obj_type_document = self.env['account.tax.support']
        if self._context.get('default_tax_support_id', False):
            return obj_type_document.browse(self._context.get('default_tax_support_id'))
        return obj_type_document.search([], limit=1)

    def _default_journal(self):
        company_id = self.env.user.company_id
        inv_type = self._context.get('type', 'out_invoice')
        if not self._context.get('default_journal_id', False):
            journal_id = company_id.property_receivable_journal_id if 'out_' in inv_type else company_id.property_payable_journal_id
            if journal_id: return journal_id
        return super(AccountInvoice, self)._default_journal()

    name = fields.Char(default='Nuevo')
    type = fields.Selection(selection_add=[('refund', 'Refund')])
    document_type = fields.Selection(selection=[
        ('invoice', 'Invoice'), ('refund', 'Refund'),
        ('clearance', 'Clearance'), ('debit', 'Debit')], string='Type Document', default='invoice', required=True)
    tax_support_id = fields.Many2one('account.tax.support', string='Tax Support',
        domain=[('active', '=', True)], default=_default_tax_support)
    type_document_id = fields.Many2one('account.type.document', string='Voucher type',
        domain=[('active', '=', True)], default=_default_document_type)
    number = fields.Char(related='sequence_number_next', string='Number', store=True, readonly=False, size=9, copy=False, default='000000000')
    internal_number = fields.Integer('Internal Number', default=0, copy=False)
    reason = fields.Char('Reason', size=200, readonly=True, states={'draft': [('readonly', False)]}, help='Enter a reason why you are generating the credit memo')
    withholding_id = fields.One2many('account.withholding', compute='_compute_amount', string='Withholding', help='Withholding applies to the invoice')
    withholding_ids = fields.One2many('account.withholding.line', 'invoice_id', string='Withholding')
    withholding_count = fields.Integer(string='Withholding Count', compute='_get_document_count', readonly=True)
    refund_count = fields.Integer(string='Refund Count', compute='_get_refund', readonly=True)
    details_tax = fields.Boolean('Details Tax', copy=False)
    discount = fields.Float(string='Additional Discount', required=True, readonly=True, copy=True,
        states={'draft': [('readonly', False)]}, default=0.0, help='Additional discount applies only to VAT other than zero.')
    subtotal = fields.Float(string='Subtotal without tax', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_discount = fields.Float(string='Discount', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_subtotal = fields.Float(string='Subtotal', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_no_oject_tax = fields.Float(string='No Object Tax', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_no_apply_tax = fields.Float(string='No Apply Tax', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_untaxed_0 = fields.Float(string='Tax Base 0', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_base_ice = fields.Float(string='ICE Base', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_ice = fields.Float(string='ICE', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_base_irbpnr = fields.Integer(string='IRBPNR Base', store=True, readonly=True, default=0, compute='_compute_amount')
    amount_irbpnr = fields.Float(string='IRBPNR', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    total_tax = fields.Float(string="Total Tax", readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount', store=True)
    amount_tax_total = fields.Float(string="Total with Tax", store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_withhold = fields.Float(string='Withhold', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_with = fields.Float(string='Withhold Fund', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    amount_penalty = fields.Float(string='Penalty Fee', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    total = fields.Float(string='Amount Total', store=True, readonly=True, digits=dp.get_precision('Account'), default=0.0, compute='_compute_amount')
    apply_tip = fields.Boolean(string='Tip Apply', default=False, copy=False)
    total_tip = fields.Float(string='Tip Total', store=True, readonly=True, digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount')
    tip_rate = fields.Float(related='company_id.tip_rate', store=False, readonly=True, string="Tip Rate")
    
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term',
        readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]},
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. If you keep the payment terms and the due date empty, it means direct payment. "
             "The payment terms may compute several due dates, for example 50% now, 50% in one month.")
    payment_method_ids = fields.One2many('account.move.method.payment', 'invoice_id', string='Way to pays',
        readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]}, copy=True)
    method_id = fields.Many2one('account.method.payment', string='Payment Method', copy=False,
        readonly=True, states={'draft': [('readonly', False)]}, help='Choose the form of payment made by the client')
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', copy=True,
        readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Invoice address for current sales order.")
    
    establishment_id = fields.Many2one(comodel_name='res.establishment', string='Business Store', copy=True,
        readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    authorization_id = fields.Many2one('account.authorization', string='Authorization', copy=True,
        readonly=True, states={'draft': [('readonly', False)]}, default=_default_authorization, track_visibility='always')
    manual_sequence = fields.Boolean(related='authorization_id.manual_sequence')
    is_electronic = fields.Boolean(string='Is electronic', copy=True,
        default=True, help='Select you have the possibility of sending the electronic document to the SRI')
    authorization = fields.Boolean(string='Authorized by SRI', copy=False, help='Selected indicates that the invoice is authorized by the SRI')
    received = fields.Boolean('Received by SRI', copy=False, help='Selected indicates that the invoice is received by the SRI')
    authorization_number = fields.Char('N° authorization', size=49, copy=False, readonly=True,
        states={'draft': [('readonly', False)]}, help='Authorization number validated by SRI')
    access_key = fields.Char('Access key', size=49, copy=False, help='Access code generated by the company to be validated')
    authorization_date = fields.Char('Authorization date', size=100, copy=False, readonly=True,
        states={'draft': [('readonly', False)]},help='Authorization date validated by SRI')
    environment = fields.Char('Environment', size=50, copy=False, readonly=True, states={'draft': [('readonly', False)]})
    emission_code = fields.Char('Type the emssion', size=1, default='2', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    message_state = fields.Char('Message Authorization', size=25, copy=False, readonly=True, states={'draft': [('readonly', False)]})
    line_info_ids = fields.One2many('additional.info', 'invoice_id', string='Information Additional Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    statement_tax_line_ids = fields.One2many('account.statement.tax', 'invoice_id',
        string='Statement', readonly=True, states={'draft': [('readonly', False)]}, copy=False)

    #refund_document_id = fields.Many2one('account.type.document', string='Voucher type', domain=[('active', '=', True)], track_visibility='always')
    tmpl_entity = fields.Char('Temporary Entity', size=3, help='Entity')
    tmpl_emission = fields.Char('Temporary Emission', size=3, help='Emission')
    tmpl_number = fields.Char('Temporary Number', size=9, help='Number')
    tmpl_invoice_date = fields.Date('Temporary Date invoice', copy=False, help='Date emission relation to document')
    attachment_number = fields.Integer(compute='_get_attachment_number', string="Number of Attachments")
    is_refund = fields.Boolean(copy=True, help='It is a refund type document')
    account_refund_ids = fields.One2many('account.refund.invoice', 'refund_invoice_id', string='Refunds')
    refund_ids = fields.Many2many('account.invoice', 'refund_invoice_rel', 'refund_id', 'invoice_id', string='Refunds',
        readonly=True, states={'draft': [('readonly', False)]}, copy=False)


    @api.model_cr
    def init(self):
        cr = self.env.cr
        for xsql in List_Alter_Table:
            cr.execute(xsql)


    @api.constrains('number', 'authorization_id', 'type_document_id',  'company_id', 'type', 'state')
    def _check_number(self):
        for inv in self.filtered(lambda i: i.state != 'draft'):
            domain = [('number', '=', inv.number), ('company_id', '=', inv.company_id.id), ('type_document_id', '=', inv.type_document_id.id),
                      ('type', '=', inv.type), ('authorization_id', '=', inv.authorization_id.id), ('state', '!=', 'draft')]
            unique_number = self.search(domain)
            for x in unique_number:
                if x.id != inv.id and x.name == inv.name and x.internal_number == inv.internal_number:
                    raise UserError(_('Invoice Number must be unique per company!'))


    @api.constrains('line_info_ids')
    def _check_limit_additional(self):
        if len(self.line_info_ids) > 16:
            raise UserError(_('You must enter 14 additional fields as maximum in XML document allowed by the SRI.'))


    @api.model
    def create(self, vals):
        if 'method_id' not in vals:
            vals['method_id'] = self._default_method_payment().id
        company = self.env.user.company_id
        if 'account_id' not in vals:
            partner_id = self.env['res.partner'].browse(vals['partner_id'])
            vals['account_id'] = partner_id.property_account_receivable_id.id or company.property_account_receivable_id.id
        return super(AccountInvoice, self.with_context(mail_create_nolog=True)).create(vals)

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None, form=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                    description=description, journal_id=journal_id, form=form)
            refund_invoice = self.create(values)
            invoice_type = {'out_invoice': ('customer invoices credit note'),
                'in_invoice': ('vendor bill credit note')}
            message = _("This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (invoice_type[invoice.type], invoice.id, invoice.number)
            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices


    @api.model
    def _refund_cleanup_lines(self, lines):
        result = super(AccountInvoice, self)._refund_cleanup_lines(lines)
        for line in result:
            tax_ids = self.env['account.tax']
            if 'invoice_line_tax_ids' in line[2]:
                for line_tax in line[2]['invoice_line_tax_ids']:
                    tax_ids += self.env['account.tax'].browse(line_tax[2])
            else:
                tax_ids += self.env['account.tax'].browse(line[2]['tax_id'])
            tax_tag_ids = tax_ids.mapped('tag_ids').filtered(lambda l: 'refund' in l.document_type)
            line[2]['tax_tag_ids'] = [(6, 0,  tax_tag_ids.ids)]
        return result

    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None, form=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id)
        values['name'] = _('New')
        values['tmpl_entity'] = invoice.authorization_id.entity
        values['tmpl_emission'] = invoice.authorization_id.issue
        values['tmpl_number'] = invoice.number
        values['tmpl_invoice_date'] = invoice.date_invoice
        values['origin'] = invoice.name
        values['partner_id'] = invoice.partner_id.id
        values['type_document_id'] = form.type_document_id.id if form.type_document_id else False
        values['authorization_id'] = form.authorization_id.id if form.authorization_id else False
        values['reason'] = description or ''
        values['number'] = '000000000'
        if form.type in ['in_refund']:
            values['tax_support_id'] = form.tax_support_id.id if form.tax_support_id else False
            values['number'] = form.number if form.number else False
        return values


    @api.onchange('authorization_id')
    def _onchange_authorization_id(self):
        res = {'value': {}}
        if self.authorization_id:
            lines_info = []
            self.line_info_ids = [(6, 0, [])]
            if len(self.authorization_id.line_info_ids):
                for line in self.authorization_id.line_info_ids:
                    lines_info.append((0, 0, {
                        'sequence': line.sequence,
                        'name': line.name,
                        'value_tag': line.value_tag,
                    }))
                res['value']['line_info_ids'] = lines_info
        return res


    @api.onchange('type_document_id', 'is_electronic', 'partner_id', 'user_id')
    def _onchange_is_electronic(self):
        domain = self._domain_authorization(self.partner_id.id, self.type_document_id.id, self.is_electronic, self.type)
        default_type_document = bool(self.type_document_id.code=='03')
        vals = {
            'received': True if 'in_' in self.type and self.is_electronic and not default_type_document else False,
            'authorization': True if 'in_' in self.type and self.is_electronic and not default_type_document else False,
        }
        if self.partner_id and self.partner_id.method_id:
            vals.update({'method_id': self.partner_id.method_id.id})
        self.update(vals)
        return {'domain': {'authorization_id': domain}}

    
    def _domain_authorization(self, partner_id, type_document_id, is_electronic=True, xtype='out_invoice'):
        user = self.user_id or self.env.user
        domain = [('type_document_id', '=', type_document_id),
                  ('is_electronic', '=',  is_electronic), ('company_id', '=', user.company_id.id)]
        if 'in_' in xtype:
            domain += [('type', '=', 'internal' if self.type_document_id.code=='03' else 'external')]
            if self.type_document_id.code!='03':
                domain += [('partner_id', '=', partner_id)]
        else:
            domain += [('type', '=', 'internal')]
            ids = user.authorization_ids.ids
            if len(ids) > 1: domain += [('id', 'in', ids)]
        return domain


    @api.onchange('number')
    def _onchange_authorization_number(self):
        number = '%%0%sd' % 9 % 0
        if 'default_number' in self._context:
            self.number = int(self._context.get('default_number'))
        if self.number:
            number = '%%0%sd' % 9 % int(self.number)
        self.number = number


    @api.onchange('tax_support_id')
    def _onchange_tax_support_id(self):
        res = {}
        if self.tax_support_id and 'in_' in self.type:
            res['domain'] = {'type_document_id': [('id', 'in', self.tax_support_id.document_ids.ids)]}
        return res


    @api.onchange('tmpl_entity', 'tmpl_emission', 'tmpl_number')
    def _onchange_tmpl_invoice(self):
        if self.tmpl_entity and self.tmpl_emission and self.tmpl_number:
            if len(self.tmpl_entity) < 3 or len(self.tmpl_emission) < 3 or len(self.tmpl_number) < 9:
                raise UserError(_('The invoice number is incomplete'))
            else:
                self.origin = '%s-%s-%s' % (self.tmpl_entity, self.tmpl_emission, self.tmpl_number)
                invoice = self.env['account.invoice'].search([('name', '=', self.origin), ('partner_id', '=', self.partner_id.id)], limit=1) or False
                self.invoice_id = invoice.id if invoice else False
                self.tmpl_invoice_date = invoice.date_invoice if invoice else False


    def _get_authorization(self, domain):
        auth = self.env['account.authorization'].search(domain, limit=1, order="id asc")
        return auth
    

    @api.multi
    def refresh_invoice(self):
        invoice_ids = self.search([])
        for record in self.web_progress_iter(invoice_ids, "({})".format(self._description)):
            for line in record.invoice_line_ids:
                line._compute_price()
                line._compute_amount()
            vdetail = True if record.details_tax else False
            record.details_tax = vdetail
            

    def _prepare_tax_line_vals(self, line, tax):
        """ Prepare values to create an account.invoice.tax line

        The line parameter is an account.invoice.line, and the
        tax parameter is the output of account.tax.compute_all().
        """
        tax['amount'] = '{:.4f}'.format(tax['amount'])
        tax['base'] = '{:.4f}'.format(tax['base'])
        vals = {
            'invoice_id': self.id,
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': float(tax['amount']),
            'base': float(tax['base']),
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
            'account_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
            'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
        }

        # If the taxes generate moves on the same financial account as the invoice line,
        # propagate the analytic account from the invoice line to the tax line.
        # This is necessary in situations were (part of) the taxes cannot be reclaimed,
        # to ensure the tax move is allocated to the proper analytic account.
        if not vals.get('account_analytic_id') and line.account_analytic_id and vals['account_id'] == line.account_id.id:
            vals['account_analytic_id'] = line.account_analytic_id.id
        return vals


    def _default_method_payment(self):
        obj_method = self.env['account.method.payment']
        if self._context.get('default_method_id', False):
            return obj_method.browse(self._context.get('default_method_id'))
        if self.partner_id.method_id:
            return self.partner_id.method_id
        return obj_method.search([('code', '=', '20')])


    def _get_contents(self, line):
        currency_id = self.currency_id
        if not line.payment_id and not line.withholding_id:
            document_name = _('Credit note')
        elif line.withholding_id:
            document_name = _('Withholding')
        elif line.payment_id:
            document_name = _('Payment')
        else:
            document_name = _('Cross')
        # get the outstanding residual value in invoice currency
        if line.currency_id and line.currency_id == self.currency_id:
            amount_to_show = abs(line.amount_residual_currency)
        else:
            amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(abs(line.amount_residual), self.currency_id)
        if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
            return {}
        content = {
            'journal_name': '%s %s' % (document_name, line.date),
            'amount': amount_to_show,
            'currency': currency_id.symbol,
            'id': line.id,
            'position': currency_id.position,
            'digits': [69, self.currency_id.decimal_places],
        }
        return content


    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('account_id', '=', self.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False),
                      ('move_id.state', '=', 'posted'),
                      '|',
                        '&', ('amount_residual_currency', '!=', 0.0), ('currency_id','!=', None),
                        '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id','=', None), ('amount_residual', '!=', 0.0)]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            if len(lines):
                contents = []
                for line in lines:
                    contents.append(self._get_contents(line))
                info['content'] = contents
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True


    @api.multi
    def _get_payments_vals(self):
        ret = super(AccountInvoice, self)._get_payments_vals()
        for line in ret:
            move_line = self.env['account.move.line'].browse(line['payment_id'])
            cross = False
            if not move_line.payment_id and not move_line.withholding_id:
                cross = True
                document_name = _('Credit note')
            elif move_line.withholding_id:
                document_name = _('Withholding')
            elif move_line.payment_id:
                document_name = _('Payment')
            else:
                document_name = _('Cross')
            line.update({
                'title': '%s %s' % (document_name, line['date']),
                'withholding_id': move_line.withholding_id and move_line.withholding_id.id or False,
                'cross': cross,
            })
        return ret


    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        if not len(self.invoice_line_ids): return tax_grouped
        amount_tax_total = amount_witout_tax = 0.0
        for line in self.invoice_line_ids:
            compare_r = float_compare(line.price_subtotal, line.price_total, precision_digits=6)
            amount_witout_tax += line.price_subtotal if compare_r else 0.0
            amount_tax_total += line.price_tax
        amount_tax_total = float('{:.4f}'.format(amount_tax_total))
        amount_witout_tax = float('{:.4f}'.format(amount_witout_tax))
        
        for line in self.invoice_line_ids:
            taxes = list()
            price_unit = line._get_discounted_price_unit()
            
            obj_ice = self.env['account.tax']
            obj_irbpnr = self.env['account.tax']
            obj_iva = self.env['account.tax']

            amount_irbpnr = line.quantity
            amount_ice = 0.0

            for tax in line.invoice_line_tax_ids:
                if tax.tax_group_id.type == 'irbpnr': obj_irbpnr += tax
                elif tax.tax_group_id.type in ['iva', 'iva0', 'nobiva', 'exiva']: obj_iva += tax
                elif tax.tax_group_id.type == 'ice': obj_ice += tax
 
            tax_ice = obj_ice.compute_all(price_unit, None, line.quantity, line.product_id, self.partner_id)
            taxes += tax_ice['taxes']
            amount_ice = tax_ice['total_included'] - tax_ice['total_excluded']
            tax_irbpnr = obj_irbpnr.with_context(base_values=[amount_irbpnr, amount_irbpnr, amount_irbpnr]).compute_all(price_unit, None, line.quantity, line.product_id, self.partner_id)
            taxes += tax_irbpnr['taxes']
            base_iva = (price_unit * line.quantity) + amount_ice
            tax_iva = obj_iva.with_context(base_values=[base_iva, base_iva, base_iva]).compute_all(price_unit, None, line.quantity, line.product_id, self.partner_id)
            taxes += tax_iva['taxes']
            
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']

        """for key in tax_grouped:
            tax_id = self.env['account.tax'].browse(tax_grouped[key]['tax_id'])
            if tax_id.tax_group_id.type == 'iva':
                tmp_base = tax_grouped[key]['base']
                amount_tax_sum = tax_grouped[key]['amount']
                amount_tax_cal = (tmp_base * tax_id.amount)/100
                
                compare_b = float_compare(tmp_base, amount_witout_tax, precision_digits=2)
                compare_st = float_compare(amount_tax_sum, amount_tax_total, precision_digits=2)
                compare_ct = float_compare(amount_tax_cal, amount_tax_total, precision_digits=2)
                if compare_b in [-1, 1]:
                    tax_grouped[key]['base'] = amount_witout_tax
                if compare_st in [-1, 1] and compare_ct in [-1, 1]:
                    #tax_grouped[key]['amount'] = amount_tax_total
                    tax_grouped[key]['amount'] = amount_tax_cal"""
        return tax_grouped

    def truncate(self, amount):
        prec = self.env.user.company_id.currency_id.decimal_places
        multiplier = 10 ** prec
        return int(amount * multiplier) / multiplier

    def _refresh_lines_taxes(self, tax_grouped):
        for key in tax_grouped:
            domain = [('invoice_id', '=', tax_grouped[key]['invoice_id']), ('name', '=', tax_grouped[key]['name']), ('tax_id', '=', tax_grouped[key]['tax_id'])]
            line_tax = self.env['account.invoice.tax'].search(domain)
            vals = tax_grouped[key]
            line_tax.write(vals)


    @api.multi
    def _set_sequence_next(self):
        if not self.authorization_id or self.manual_sequence or not self.sequence_number_next:
            return False
        self.authorization_id._set_sequence_next("account_invoice", "('open', 'paid', 'cancel')")


    def _generate_key_access(self):
        if self.is_electronic and self.type_document_id.code_doc_xml and (not\
            self.access_key or not self.received or not self.authorization):
            access_key = self.authorization_id.generation_access_key(self.name, self.type_document_id, self.date_invoice)
        else:
            access_key = self.access_key
        return access_key


    @api.multi
    def _check_duplicate_supplier_reference(self):
        pass

    @api.multi
    def action_create_statement_tax(self):
        obj_tax = self.env['account.tax']
        obj_statement = self.env['account.statement.tax']
        for invoice in self:
            statement_ids = dict()
            invoice.statement_tax_line_ids.unlink()
            for tax_line in invoice.tax_line_ids:
                tax_id = tax_line.tax_id
                for tag_id in tax_id.tag_ids.filtered(lambda t: t.document_type==invoice.type):
                    key = '%s-%s' % (tax_id.id, tag_id.name)
                    if key not in statement_ids:
                        statement_ids[key] = {
                            'invoice_id': invoice.id,
                            'form_id': tag_id.form_id and tag_id.form_id.id or False,
                            'name': tag_id.name,
                            'tax_group_id': tax_id.tax_group_id and tax_id.tax_group_id.id,
                            'base': 0.0,
                            'percentage': tax_id.amount,
                            'amount': 0.0
                        }
                    statement_ids[key]['base'] += tax_line.base
                    statement_ids[key]['amount'] += tax_line.amount
            invoice_line_ids = invoice.invoice_line_ids.sorted(lambda x: x.price_subtotal)
            for line in invoice_line_ids:
                statement_line_ids = dict()
                line.statement_tax_line_ids.unlink()
                currency = line.invoice_id and line.invoice_id.currency_id or False
                price_unit = (line.price_unit* (1 - (line.discount or 0.0) / 100.0))
                tax_obj = line.invoice_line_tax_ids.compute_all(price_unit, currency=currency,
                    quantity=line.quantity, product=line.product_id, partner=invoice.partner_id)
                taxes = sorted(tax_obj["taxes"], key=lambda k: k["sequence"])
                for tax in taxes:
                    for tag_id in obj_tax.browse(tax['id']).tag_ids.filtered(lambda t: t.document_type==invoice.type):
                        key = '%s-%s' % (tax['id'], tag_id.name)
                        form_dict = statement_ids[key]
                        if key not in statement_line_ids:
                            statement_line_ids[key] = {
                            'invoice_line_id': line.id,
                            'form_id': form_dict['form_id'],
                            'name': form_dict['name'],
                            'tax_group_id': form_dict['tax_group_id'],
                            'base': 0.0,
                            'percentage': form_dict['percentage'],
                            'amount': 0.0,  
                            }
                        statement_line_ids[key]['base'] += tax['base']
                        statement_line_ids[key]['amount'] += tax['amount']

                for key, vals in statement_line_ids.items():
                    obj_statement.create(vals)
            for key, vals in statement_ids.items():
                obj_statement.create(vals)

    @api.multi
    def invoice_validate(self):
        self._check_duplicate_supplier_reference()
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.partner_id.limit_amount > 0.0 and inv.amount_total > inv.partner_id.limit_amount):
            raise UserError(_('You can not send an invoice with a total of more than USD when you are the'))
        if to_open_invoices.filtered(lambda inv: inv.amount_total == 0.0):
            raise UserError(_('You can not create an invoice with an amount of 0.0'))
        if to_open_invoices.filtered(lambda inv: inv.is_refund and inv.type in ['out_invoice']):
            taxes = [line.mapped('invoice_line_tax_ids').filtered(lambda l: l.tax_group_id.type != 'iva0').ids for line in to_open_invoices.invoice_line_ids][0]
            if taxes: raise UserError(_('This document is applying refund, you should not apply tax different from 0'))
            amount_refund = sum(line.total for line in to_open_invoices.refund_ids)
            if float_compare(to_open_invoices.amount_total, amount_refund, precision_digits=4) != 0:
                raise UserError(_('Total invoice amount %s is not equal to refund amount %s') % (to_open_invoices.amount_total, amount_refund))
        return super(AccountInvoice, self).invoice_validate()


    @api.multi
    def action_invoice_open(self):
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state != 'draft'):
            raise UserError(_("Invoice must be in draft state in order to validate it."))
        if to_open_invoices.filtered(lambda inv: float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1):
            raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead."))
        for invoice in to_open_invoices:
            # Increase of presence in tax
            sequence_count = defaultdict(int)
            for tax_line in invoice.mapped('tax_line_ids').filtered(lambda l: l.tax_id):
                sequence_count[tax_line.tax_id] += 1
            for tax, count in sequence_count.items():
                tax._increase_rank('sequence', count)
            invoice._review_tax_invoice()
            invoice._get_sequence()
            invoice.action_payment_methods()
            invoice.action_date_assign()
            invoice.action_move_create()
            invoice.action_create_statement_tax()
            invoice.write({'state': 'open', 'access_key': invoice._generate_key_access()})
            invoice.move_id.write({
                'tax_support_id': invoice.tax_support_id and invoice.tax_support_id.id or False,
                'type_document_id': invoice.type_document_id and invoice.type_document_id.id or False,
                'authorization': invoice.is_electronic and invoice.access_key or invoice.authorization_id.name,
                'origin': invoice.name or False,
            })
        return to_open_invoices.invoice_validate()


    def _get_sequence(self):
        padding = 9
        if not self.authorization_id.manual_sequence:
            if not self.authorization_id.sequence_id and self.authorization_id.is_electronic and self.authorization_id.type == 'internal':
                raise UserError(_('The authorizations do not have a sequence!'))
            sequence_id = self.authorization_id.sequence_id._get_current_sequence()
            padding = sequence_id and sequence_id.padding
            if self.number == '000000000' or not self.number:
                name_old = self.sequence_number_next_prefix + self.sequence_number_next
                if name_old != self.name or self.number == '000000000':
                    internal_number = sequence_id.number_next_actual
            else:
                internal_number = int(self.number)
        else:
            if self.number == '000000000': raise UserError(_('Enter the document number!'))
            internal_number = int(self.number)
        sequence_number_next = '%%0%sd' % padding % internal_number
        name = '%s%s' % (self.sequence_number_next_prefix, sequence_number_next)
        self.write({'name': name, 'number': sequence_number_next, 'internal_number': internal_number})

    @api.multi
    def action_invoice_draft(self):
        #for record in self.web_progress_iter(self, _('Record draft') + "({})".format(self._description)):
        for record in self:
            if not record.manual_sequence:
                internal_number = 0
                number = '000000000'
            else:
                internal_number = record.internal_number
                number = record.number
            super(AccountInvoice, record).action_invoice_draft()
            if not record.manual_sequence:
                sequence_id = record.authorization_id.sequence_id._get_current_sequence()
                record.sequence_number_next = '%%0%sd' % sequence_id.padding % sequence_id.number_next_actual
            record.write({'number': number, 'internal_number': internal_number})

    @api.multi
    def action_invoice_cancel(self):
        #for record in self.web_progress_iter(self, _('Record cancel ') + "({})".format(self._description)):
        for record in self:
            if record.withholding_count >= 1:
                domain = [ ('partner_id', '=', record.partner_id.id), '|', ('tmpl_invoice_number', '=', record.name), ('invoice_id', '=', record.id)]
                withhold_line_ids = self.env['account.withholding.line'].search(domain)
                withholds = withhold_line_ids.mapped('withholding_id')
                for withhold in withholds.filtered(lambda x: x.state == 'approved'):
                    move_ids = withhold.mapped('move_id')
                    move_ids.line_ids.remove_move_reconcile()
            if record.filtered(lambda inv: inv.state not in ['draft', 'open']):
                raise UserError(_("Invoice must be in draft or open state in order to be cancelled."))
            record.action_cancel()


    @api.multi
    def action_invoice_paid(self):
        values = {'state': 'paid'}
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        if to_pay_invoices.filtered(lambda inv: inv.state != 'open'):
            raise UserError(_('Invoice must be validated in order to set it to register payment.'))
        if to_pay_invoices.filtered(lambda inv: not inv.reconciled):
            raise UserError(_('You cannot pay an invoice which is partially paid. You need to reconcile payment entries first.'))
        line_residual = self.move_id.line_ids.filtered(lambda line: line.account_id.reconcile and line.account_id.user_type_id.type in ['receivable','payable'])
        for line in line_residual:
            if self.account_id != line.account_id:
                values.update({'account_id': line.account_id.id})
                msg = _('A change was made in the invoice from %s to %s') % (self.account_id.display_name, line.account_id.display_name)
                self.message_post(body=msg)
        return to_pay_invoices.write(values)


    @api.multi
    def name_get(self):
        result = []
        for inv in self:
            result.append((inv.id, "%s" % inv.name or ''))
        return result

    
    def _get_line_withholding(self):
        vals = {
            'sequence': 10,
            'name': 'renta',
            'invoice_id': self.id,
            'tmpl_invoice_date': self.date_invoice,
            'tmpl_invoice_number': self.name,
            'livelihood_id': self.type_document_id.id,
            'type_withhold': 'percent',
            'amount_base': self.amount_subtotal,
        }
        return vals
            

    @api.multi
    def action_create_withholding(self):
        lines = []
        type_document = self.env['account.type.document'].search([('code', '=', '07')], limit=1).id        
        if self.type == 'in_invoice':
            action_name = 'oe_account.action_withholding_purchase_form'
            xml_name = 'oe_account.view_withholding_purchase_form'
        else:
            action_name = 'oe_account.action_withholding_sale_form'
            xml_name = 'oe_account.view_withholding_sale_form'
        vals = self._get_line_withholding()
        lines.append(vals)
        action = self.env.ref(action_name).read()[0]
        action.update({
            'views': [(self.env.ref(xml_name).id, 'form')],
            'context': self.with_context(default_document_type='withhold',
                                         default_type_document_id=type_document,
                                         default_date_withholding=self.date_invoice,
                                         default_withholding_line_ids=lines,
                                         default_partner_id=self.partner_id.id,
                                         default_type=TYPEWIHHOLDING[self.type],
                                         default_origin=self.name,
                                         default_reference=self.reference,
                                         default_account_id=self.account_id.id,
                                         default_journal_id=self.journal_id.id)._context,
        })
        return action

    
    @api.multi
    def action_wiew_withholdings(self):
        withholding_ids = self.env['account.withholding.line'].search([('invoice_id', '=', self.id)])
        withhold_ids = withholding_ids.mapped('withholding_id').filtered(lambda w: w.document_type=='withhold')
        if self.type == 'out_invoice':
            action_name = 'oe_account.action_withholding_sale_form'
            xml_name = 'oe_account.view_withholding_sale_form'
        else:
            action_name = 'oe_account.action_withholding_purchase_form'
            xml_name = 'oe_account.view_withholding_purchase_form'
        action = self.env.ref(action_name).read()[0]
        if len(withhold_ids) > 1:
            action['domain'] = [('id', 'in', withhold_ids.ids)]
        elif len(withhold_ids) == 1:
            action['views'] = [(self.env.ref(xml_name).id, 'form')]
            action['res_id'] = withhold_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


    @api.multi
    def action_open_refunds(self):
        if self.type == 'out_invoice':
            action = self.env.ref('account.action_invoice_out_refund').read()[0]
        elif self.type == 'in_invoice':
            action = self.env.ref('account.action_invoice_in_refund').read()[0]
        action.update({
            'context': self.with_context(search_default_refund_invoice_id=self.id,
                                         search_default_origin=self.name)._context,
        })
        return action


    def _action_invoice_sent(self):
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="account.mail_template_data_notification_email_account_invoice",
            force_email=True
        )
        return ctx, compose_form


    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        ctx, compose_form = self._action_invoice_sent()
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }


    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an invoice which is not draft or cancelled. You should create a credit note instead.'))
            elif invoice.type in ['out_invoice', 'out_refund'] and invoice.authorization:
                raise UserError(_('You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return models.Model.unlink(self)


    @api.multi
    def _get_tax_amount_by_group(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        fmt = partial(formatLang, self.with_context(lang=self.partner_id.lang).env, currency_obj=currency)
        res = {}
        for line in self.tax_line_ids:
            typevat = line.tax_id.tax_group_id.type
            res.setdefault(line.tax_id.tax_group_id, {'percentage': line.tax_id.amount, 'base': 0.0, 'amount': 0.0, 'type': typevat})
            res[line.tax_id.tax_group_id]['amount'] += line.amount
            res[line.tax_id.tax_group_id]['base'] += line.base
        res = sorted(res.items(), key=lambda l: l[0].sequence)
        res = [(
            r[0].name, r[1]['percentage'], r[1]['amount'], r[1]['base'],
            fmt(r[1]['amount']), fmt(r[1]['base']), r[1]['type']) for r in res]
        for withhold_id in self.withholding_ids.mapped('withholding_id').filtered(lambda l: l.state=='approved'):
            res.append((withhold_id.type_document_id.name, 0.0, withhold_id.amount_total, 0.0,
                fmt(withhold_id.amount_total), fmt(0.0), 'renta'))
        return res


    @api.multi
    def _get_payments(self):
        self.ensure_one()
        list_payment = []
        if len(list_payment) == 0:
            list_payment.append({
                'formaPago': self.method_id.name,
                'total': '{:.2f}'.format(self.total),
            })
        return list_payment


    def _get_payment_time(self):
        payment = {
            'plazo': 1,
            'unidadTiempo': 'dias',
        }
        if self.payment_term_id:
            day = sum(line.days for line in self.payment_term_id.line_ids)
            if day > 0: payment['plazo'] = day
        return payment


    def _get_payment_shape(self):
        list_payment = []
        """for line in self.payment_ids:
            pay = {
                'formaPago': line.method_id.code,
                'total': '{:.2f}'.format(line.amount),
                'plazo': 1,
            }
            pay.update(self._get_payment_time())
            list_payment.append(pay)"""
        if len(list_payment) == 0:
            pay = {
                'formaPago': self.method_id.code,
                'total': '{:.2f}'.format(self.total),
                'plazo': 1,
            }
            pay.update(self._get_payment_time())
            list_payment.append(pay)
        return list_payment


    def _get_withhold(self, value):
        result = [(6, 0, [])]
        lines = self._get_payments_vals()
        currency = self.env.user.company_id.currency_id
        for line in lines:
            if line.get('withholding_id', False):
                result += [(0, 0, {
                    'sequence': 1,
                    'method_id': self.env.ref('oe_account.payment_method_20').id,
                    'date_due': line['date'],
                    'days': 0,
                    'value': 'fixed',
                    'value_amount': 0.0,
                    'amount': line.get('amount', 0.0),
                    'currency_id': currency and currency.id,
                })]
                value -= line.get('amount', 0.0)
        return value, result


    def _get_list_payments(self, value):
        lines_payment = []
        pterm_list = self.payment_term_id.with_context(currency_id=self.company_id.currency_id.id).\
            _list_compute(value=value, date_ref=self.date_invoice)
        for line in pterm_list[0]:
            lines_payment += [(0, 0, line)]
        return lines_payment


    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self._get_currency_rate_date() or fields.Date.context_today(self))
                if not (line.get('currency_id') and line.get('amount_currency')):
                    line['currency_id'] = currency.id
                    line['amount_currency'] = line['price']
                    line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = line['price']
            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, invoice_move_lines


    def _review_tax_invoice(self):
        for line in self.invoice_line_ids:
            list_0 = list()
            list_ice = list()
            list_iva = list()
            list_iva += [tax.id for tax in line.invoice_line_tax_ids if tax.tax_group_id.type in ['iva', 'nobiva', 'exiva']]
            list_0 += [tax.id for tax in line.invoice_line_tax_ids if tax.tax_group_id.type == 'iva0']
            list_ice += [tax.id for tax in line.invoice_line_tax_ids if tax.tax_group_id.type == 'ice']
            ref_name = line.product_id and line.product_id.name or line.name
            if len(line.invoice_line_tax_ids):
                if len(list_ice):
                    if len(list_iva) == 0:
                        raise UserError(_('Can not add only ICE to invoice line enter VAT other than 0: %s') % ref_name)
                    if len(list_0):
                        raise UserError(_('You should not add an ICE together with VAT 0: %s') % ref_name)
                if not len(list_iva) and not len(list_0):
                    raise UserError(_('You must enter at least one VAT tax on the product line to invoice: %s') % ref_name)
            else:
                raise UserError(_('You must enter at least one tax for each line of the invoice, including tax 0 VAT: %s') % ref_name)
        return True


    @api.multi
    def action_get_attachment_tree_view(self):
        attachment_action = self.env.ref('base.action_attachment')
        action = attachment_action.read()[0]
        action['context'] = {'default_res_model': self._name, 'default_res_id': self.ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        action['search_view_id'] = (self.env.ref('oe_account.ir_attachment_view_search_inherit_oe_account').id, )
        return action


    @api.multi
    def _get_attachment_number(self):
        read_group_res = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'account.invoice'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attach_data = dict((res['res_id'], res['res_id_count']) for res in read_group_res)
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)


    @api.onchange('is_refund', 'refund_ids', 'invoice_line_ids')
    def _onchange_refund(self):
        company_id = self.env.user.company_id
        if self.is_refund:
            tax = []
            if not company_id.refund_product_id:
                action = self.env.ref('account.action_account_config')
                msg = _('Unable to find defined reimbursement product for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            for line in self.invoice_line_ids:
                tax += line.mapped('invoice_line_tax_ids').filtered(lambda l: l.tax_group_id.type != 'iva0').ids
            if tax:
                raise UserError(_('This document is applying refund, you should not apply tax different from 0'))
            invoice_line = self.invoice_line_ids and self.invoice_line_ids[0] or []
            amount_refund = sum(line.total for line in self.refund_ids)
            if invoice_line:
                invoice_line.price_unit = amount_refund


    @api.multi
    def _settings_data(self, vals):
        for inv in self:
            for line in inv.tax_line_ids:
                if line.tax_id.id in vals:
                    if inv.add_discount > 0.0:
                        amount = vals[line.tax_id.id]['amount'] - line.amount_total
                        line.write({'manual': True, 'amount_rounding': amount})
                    else:
                        line.amount_rounding = vals[line.tax_id.id]['amount']


    @api.model
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            tax = tax_line.tax_id
            if tax.amount_type == "group":
                for child_tax in tax.children_tax_ids:
                    done_taxes.append(child_tax.id)
            res.append({
                'invoice_tax_line_id': tax_line.id,
                'tax_line_id': tax_line.tax_id.id,
                'type': 'tax',
                'name': tax_line.name,
                'price_unit': tax_line.amount_total,
                'quantity': 1,
                'price': tax_line.amount_total,
                'account_id': tax_line.account_id.id,
                'account_analytic_id': tax_line.account_analytic_id.id,
                'invoice_id': self.id,
                'tax_ids': [(6, 0, list(done_taxes))] if done_taxes and tax_line.tax_id.include_base_amount else [],
                'tax_tag_ids': [(6, 0, tax_line.tax_tag_ids.ids)],
            })
            done_taxes.append(tax.id)
        return res

    @api.multi
    def action_payment_methods(self):
        if not self.payment_term_id:
            self.payment_term_id = self.env.ref('account.account_payment_term_immediate').id
        if not len(self.payment_method_ids) or self._context.get('refresh', False):
            lines = [(6, 0, [])]
            lines += self._get_list_payments(self.amount_total)
            self.write({'payment_method_ids': lines})
        amount_payment = sum(line.amount for line in self.payment_method_ids)
        #if float_compare(self.amount_total, amount_payment, precision_digits=2) != 0:
        #    raise UserError(_('There is a discrepancy in the value of forms of payment with the total of the invoice.'))

    def _prepare_payment_vals(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None, communication=None):
        payment_vals = super(AccountInvoiceLine, self)._prepare_payment_vals(pay_journal, pay_amount, date, writeoff_acc, communication)
        payment_vals.update({'document_number': payment_vals['communication'], 'communication': False})
        return payment_vals

    @api.multi
    def action_view_payments(self):
        record_ids = self.mapped('payment_ids')
        action_name = 'account.action_account_payments' if 'out_' in self.type else 'account.action_account_payments_payable'
        action = self.env.ref(action_name).read()[0]
        action.update({
            'context': self.with_context(installment=True)._context,
        })
        if len(record_ids) > 1:
            action['domain'] = [('id', 'in', record_ids.ids)]
        elif len(record_ids) == 1:
            action['views'] = [(self.env.ref('account.view_account_payment_form').id, 'form')]
            action['res_id'] = record_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'


    @api.model
    def _default_account(self):
        ret = super(AccountInvoiceLine, self)._default_account()
        if not ret:
            company = self.env.user.company_id
            xtype = self._context.get('type', 'out_invoice')
            account = company.property_account_income_id if xtype in ['out_invoice', 'out_refund'] else company.property_account_expense_id
            ret = account and account.id or False
        return ret


    @api.depends('quantity', 'price_unit', 'invoice_line_tax_ids')
    def _compute_amount(self):
        prec = self.env.user.company_id.currency_id.decimal_places
        for line in self:
            currency = line.invoice_id and line.invoice_id.currency_id or None
            price = line._get_discounted_price_unit()
            amount_total = 0.0
            for tax in line.invoice_line_tax_ids.filtered(lambda l: l.tax_group_id.type == 'iva'):
                amount_total += float('{:.4f}'.format((line.price_subtotal * tax.amount)/100))
                multiplier = 10 ** prec
                amount_total = int(amount_total * multiplier) / multiplier
            taxes = line.invoice_line_tax_ids.compute_all(price, currency, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
            line.update({
                'price_tax': '{:.4f}'.format(amount_total),
                'price_total': taxes['total_included'],
                'price_subtotal_signed': taxes['total_excluded'],
            })


    account_id = fields.Many2one(default=_default_account)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', digits=dp.get_precision('Account'), store=True)
    type_discount = fields.Selection(selection=[('fixed', 'Fixed'), ('percent', 'Percentage')], default='percent', required=True)
    price_subtotal = fields.Float(string='Amount Total', store=True, readonly=True, digits=dp.get_precision('Account'),
                                  compute='_compute_price', help="Total amount without taxes")
    tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")
    statement_tax_line_ids = fields.One2many('account.statement.tax', 'invoice_line_id',
        string='Statement', readonly=True, copy=False)


    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice', 'invoice_id.date')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self._get_discounted_price_unit()
        taxes = {}
        if self.invoice_line_tax_ids:
            taxes.update(self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id))
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(date=self.invoice_id._get_currency_rate_date()).compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign


    def _get_discounted_price_unit(self):
        """Inheritable method for getting the unit price after applying
        discount(s).

        :rtype: float
        :return: Unit price after discount(s).
        """
        self.ensure_one()
        price_unit = 0.0
        prodig = self.env['decimal.precision'].precision_get('Product Price')
        disdig = self.env['decimal.precision'].precision_get('Discount')
        if self.discount and self.type_discount=='percent':
            price_unit = float('{:.4f}'.format(self.price_unit * (1 - self.discount / 100)))
        elif self.discount and self.type_discount=='fixed':
            subtotal = self.price_unit * self.quantity
            discount = round((self.discount * 100) / subtotal, precision_digits=disdig)
            price_unit = self.price_unit * (1 - discount / 100)
            price_unit = float('{:.4f}'.format(round(price_unit, precision_digits=prodig)))
        else:
            price_unit = float('{:.4f}'.format(self.price_unit * (1 - (self.discount or 0.0) / 100.0)))
        return price_unit


    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.invoice_id:
            return

        part = self.invoice_id.partner_id
        fpos = self.invoice_id.fiscal_position_id
        company = self.invoice_id.company_id
        currency = self.invoice_id.currency_id
        xtype = self.invoice_id.type

        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner!'),
                }
            return {'warning': warning}

        if not self.product_id:
            if xtype not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            if part.lang:
                product = self.product_id.with_context(lang=part.lang)
            else:
                product = self.product_id
            
            self.name = product.partner_ref
            account = self.get_invoice_line_account(xtype, product, fpos, company)
            if not account:
                account = company.property_account_income_id if xtype in ['out_invoice', 'out_refund'] else company.property_account_expense_id
            self.account_id = account.id
            self._set_taxes()

            if xtype in ('in_invoice', 'in_refund'):
                if product.description_purchase:
                    self.name += '\n' + product.description_purchase
            else:
                if product.description_sale:
                    self.name += '\n' + product.description_sale

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:

                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
        return {'domain': domain}


    def _set_taxes(self):
        """ Used in on_change to set taxes and price."""
        taxes = self.account_id.tax_ids
        if self.invoice_id.type in ('out_invoice', 'out_refund'):
            taxes += self.product_id.taxes_id
        else:
            taxes += self.product_id.supplier_taxes_id

        # Keep only taxes of the company
        company_id = self.company_id or self.env.user.company_id
        taxes = taxes.filtered(lambda r: r.company_id == company_id)

        self.invoice_line_tax_ids = fp_taxes = self.invoice_id.fiscal_position_id.map_tax(taxes, self.product_id, self.invoice_id.partner_id)
        
        fix_price = self.env['account.tax']._fix_tax_included_price
        if self.invoice_id.type in ('in_invoice', 'in_refund'):
            prec = self.env['decimal.precision'].precision_get('Product Price')
            if not self.price_unit or float_compare(self.price_unit, self.product_id.standard_price, precision_digits=prec) == 0:
                if self.price_unit == 0.0:
                    self.price_unit = fix_price(self.product_id.standard_price, taxes, fp_taxes)
                self._set_currency()
        else:
            if self.price_unit == 0.0:
                self.price_unit = fix_price(self.product_id.lst_price, taxes, fp_taxes)        
            self._set_currency()


    @api.onchange('account_id')
    def _onchange_account_id(self):
        if not self.account_id:
            return
        elif not self.price_unit:
            self._set_taxes()


    @api.onchange('invoice_line_tax_ids')
    def _onchange_tax_ids(self):
        tag_ids = self.env['account.account.tag']
        for tag in self.invoice_line_tax_ids.mapped('tag_ids'):
            tag_ids += tag.filtered(lambda l: l.document_type==self.invoice_id.type)
        self.tax_tag_ids = tag_ids


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    amount = fields.Float(digits=dp.get_precision('Account Total'))
    amount_total = fields.Float(string="Amount", digits=dp.get_precision('Account Total'), compute='_compute_amount_total')
    base = fields.Float(string='Base', compute='_compute_base_amount', store=True, digits=dp.get_precision('Account Total'))
    tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")


    @api.depends('amount', 'amount_rounding')
    def _compute_amount_total(self):
        for tax_line in self:
            amount_total = tax_line.amount + tax_line.amount_rounding
            amount_total = round(amount_total, precision_digits=2)
            tax_line.amount_total = amount_total

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'


    @api.one
    def _list_compute(self, value, date_ref=False):
        date_ref = date_ref or fields.Date.today()
        amount = value
        sign = value < 0 and -1 or 1
        result = []
        if self.env.context.get('currency_id'):
            currency = self.env['res.currency'].browse(self.env.context['currency_id'])
        else:
            currency = self.env.user.company_id.currency_id
        for line in self.line_ids.filtered(lambda l: l.days!=0):
            if line.value == 'fixed':
                amt = sign * round(line.value_amount, 4)
            elif line.value == 'percent':
                amt = round(value * (line.value_amount / 100.0), 4)
            elif line.value == 'balance' and amount > 0.0:
                amt = value
            elif line.value == 'balance' and amount == 0.0:
                amt = value - amount
            if amt > 0.0 and amount > 0.0:
                next_date = fields.Date.from_string(date_ref)
                if line.option == 'day_after_invoice_date':
                    next_date += relativedelta(days=line.days)
                elif line.option == 'fix_day_following_month':
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days - 1)
                elif line.option == 'last_day_following_month':
                    next_date += relativedelta(day=31, months=1)  # Getting last day of next month
                elif line.option == 'last_day_current_month':
                    next_date += relativedelta(day=31, months=0)  # Getting last day of next month
                result += [{
                    'sequence': line.sequence,
                    'method_id': self.env.ref('oe_account.payment_method_20').id,
                    'date_due': fields.Date.to_string(next_date),
                    'days': line.days,
                    'value': line.value,
                    'value_amount': line.value_amount,
                    'amount': amt,
                    'currency_id': currency and currency.id,
                }]
                amount -= amt
        return result
    
    
class AccountRefundInvoice(models.Model):
    _name = "account.refund.invoice"
    _description = "Refund Document"
    _inherits = {'account.invoice': 'invoice_id'}
    
    
    @api.one
    @api.depends('total_subtotal', 'total_tax', 'total_discount')
    def _compute_amount_refund(self):
        amount_total = self.total_subtotal + self.total_tax
        self.refund_total = amount_total + self.total_discount
    
    
    invoice_id = fields.Many2one('account.invoice', 'Invoice',  index=True, ondelete="cascade", required=True)
    total_subtotal = fields.Float(string='Subtotal without tax', digits=dp.get_precision('Account Total'), default=0.0)
    total_discount = fields.Float(string='Discount', digits=dp.get_precision('Account Total'), default=0.0)
    total_no_oject_tax = fields.Float(string='No Object Tax', digits=dp.get_precision('Account Total'), default=0.0)
    total_no_apply_tax = fields.Float(string='No Apply Tax', digits=dp.get_precision('Account Total'), default=0.0)
    total_untaxed_0 = fields.Float(string='Tax Base 0', digits=dp.get_precision('Account Total'), default=0.0)
    total_untaxed = fields.Float(string='Untaxed Amount',digits=dp.get_precision('Account Total'), default=0.0)
    total_tax = fields.Float(string='Tax difference of 0%', digits=dp.get_precision('Account Total'), default=0.0)
    total_ice = fields.Float(string='ICE', digits=dp.get_precision('Account Total'), default=0.0)
    refund_total = fields.Float(string='Total', store=True, readonly=True, 
        digits=dp.get_precision('Account Total'), default=0.0, compute='_compute_amount_refund')

    @api.model
    def create(self, vals):
        if not vals.get('is_refund') and vals.get('refund_invoice_id', False):
            invoice_id = self.env['account.invoice'].browse(vals['refund_invoice_id'])
            if invoice_id and invoice_id.is_refund:
                vals['type'] = 'refund'
        return super(AccountRefundInvoice, self).create(vals)
    
    
    @api.multi
    def unlink(self):
        oinvoice = self.invoice_id
        res = super(AccountRefundInvoice, self).unlink()
        oinvoice.unlink()
        return res
