# -*- coding: utf-8 -*-

from collections import defaultdict
import json
import re
import uuid

from odoo import api, fields, exceptions, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import float_round, float_is_zero


class AccountWithholding(models.Model):
    _name = "account.withholding"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "withholding"
    _order = "date_withholding desc, number desc, id desc"


    @api.depends('withholding_line_ids.amount_base')
    def _compute_total(self):
        for withh in self:
            withh.amount_base_iva = float_round(sum([x.amount_base for x in withh.withholding_line_ids if x.name == 'renta_iva']), 2)
            withh.amount_iva = float_round(sum([x.amount for x in withh.withholding_line_ids if x.name == 'renta_iva']), 2)
            withh.amount_base_renta = float_round(sum([x.amount_base for x in withh.withholding_line_ids if x.name == 'renta']), 2)
            withh.amount_renta = float_round(sum([x.amount for x in withh.withholding_line_ids if x.name == 'renta']), 2)
            withh.amount_base_isd = float_round(sum([x.amount_base for x in withh.withholding_line_ids if x.name not in ['renta_iva','renta']]), 2)
            withh.amount_isd = float_round(sum([x.amount for x in withh.withholding_line_ids if x.name not in ['renta_iva','renta']]), 2)
            withh.amount_refund = sum(x.amount_refund for x in withh.withholding_line_ids)
            withh.amount_total = float_round(sum([x.amount for x in withh.withholding_line_ids]), 2)


    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_withholding')
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', 'sale' if inv_type == 'in_withholding' else 'purchase'),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)


    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id


    @api.model
    def default_get(self,default_fields):
        res = super(AccountWithholding, self).default_get(default_fields)
        res['type_document_id'] = self.env['account.type.document'].search([('code', '=', '07')], limit=1).id
        if not res.get('name', False) and res.get('state') == 'draft':
            res['name'] = _('New')
        return res


    def _get_default_access_token(self):
        return str(uuid.uuid4())

    @api.one
    @api.depends('move_id', 'move_id.line_ids.amount_residual')
    def _compute_payments(self):
        invoice_lines = set()
        for line in self.move_id.line_ids.filtered(lambda l: l.account_id.id == self.account_id.id):
            invoice_lines.update(line.mapped('matched_credit_ids.credit_move_id.id'))
            invoice_lines.update(line.mapped('matched_debit_ids.debit_move_id.id'))
        self.invoice_move_line_ids = self.env['account.move.line'].browse(list(invoice_lines)).sorted()


    @api.one
    @api.depends('invoice_move_line_ids.amount_residual')
    def _get_invoice_info_JSON(self):
        self.invoices_widget = json.dumps(False)
        if self.invoice_move_line_ids:
            info = {'title': _('Less Invoice'), 'outstanding': False, 'content': self._get_invoices_vals()}
            self.invoices_widget = json.dumps(info)
    

    type_document_id = fields.Many2one('account.type.document', string='Voucher type', change_default=True, required=True, track_visibility='always')
    name = fields.Char(string='Reference/Description', index=True,
        readonly=True, states={'draft': [('readonly', False)]}, copy=False, help='The name that will be used on account move lines')
    origin = fields.Char(string='Source Document', help="Reference of the document that produced this withholding.",
        readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection(selection=[
            ('in_withholding','Sale withholding'),
            ('out_withholding','Purchase withholding')], readonly=True, index=True, change_default=True, default=lambda self: self._context.get('type', 'out_withholding'), track_visibility='always')
    document_type = fields.Selection(selection=[('withhold', 'Withhold')], string='Type Document', required=True, default='withhold')
    access_token = fields.Char('Security Token', copy=False, default=_get_default_access_token)
    number = fields.Char('Number', size=9, default="000000000", copy=False)
    internal_number = fields.Integer('Internal Number', default=0, copy=False)
    move_name = fields.Char(string='Name', readonly=True, default=False, copy=False,
        help="The technical field that contains the number assigned to the withholding, is automatically set when the withholding is validated and then stored to establish the same number again if the withholding is canceled, set in draft and validated again.")
    reference = fields.Char(string='Reference withholding', copy=False, help="The partner reference of this withholding.", readonly=True, states={'draft': [('readonly', False)]})
    comment = fields.Text('Additional Information', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
            ('draft','Draft'),
            ('approved', 'Approved'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),], string='Status', index=True, readonly=True, default='draft', track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed withholding.\n"
             " * The 'Approved' The state is used when the user creates the withholding and the withholding number is generated. Remains in an approved state when the user approves the withholding.\n"
             " * The 'Cancelled' status is used when user cancel withholding.")
    sent = fields.Boolean(readonly=True, default=False, copy=False, help="It indicates that the withholding has been sent.")
    date_withholding = fields.Date(string='Date emission', readonly=True, states={'draft': [('readonly', False)]}, index=True,
        help="Keep empty to use the current date", copy=False)
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True, required=True, track_visibility='always')
    move_id = fields.Many2one('account.move', string='Move Entry', readonly=True, index=True, ondelete='restrict', copy=False,
        help="Link to the automatically generated Items.")
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_currency, track_visibility='always')
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True, states={'draft': [('readonly', False)]}, default=_default_journal,
        domain="[('type', 'in', {'out_withholding': ['purchase'], 'in_withholding': ['sale']}.get(type, [])), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.withholding'))
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user, copy=False)
    sequence_number_next = fields.Char(string='Next Number', compute="_get_sequence_number_next", inverse="_set_sequence_next")
    sequence_number_next_prefix = fields.Char(string='Next Number', size=9, compute="_get_sequence_prefix")
    amount_base_iva = fields.Monetary(string='IVA Base', compute='_compute_total', store=True)
    amount_iva = fields.Monetary(string='Total IVA', compute='_compute_total', store=True)
    amount_base_renta = fields.Monetary(string='Renta Base', compute='_compute_total', store=True)
    amount_renta = fields.Monetary(string='Total Renta', compute='_compute_total', store=True)
    amount_base_isd = fields.Monetary(string='ISD Base', store=True, readonly=True, compute='_compute_total')
    amount_isd = fields.Monetary(string='ISD', store=True, readonly=True, compute='_compute_total')
    amount_total = fields.Monetary(string='Total', compute='_compute_total', store=True)
    amount_refund = fields.Monetary(string='Refund Amount', compute='_compute_total', store=True)
    account_id = fields.Many2one('account.account', string='Account', required=True, readonly=True, states={'draft': [('readonly', False)]},
        domain=[('deprecated', '=', False)], help="The partner account used for this withholding.")
    withholding_line_ids = fields.One2many('account.withholding.line', 'withholding_id', string='Withholding Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    authorization_id = fields.Many2one('account.authorization', string='Authorization', change_default=True, 
        required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    manual_sequence = fields.Boolean(related='authorization_id.manual_sequence')
    is_electronic = fields.Boolean(string='Is electronic', copy=True, default=True, help='Select you have the possibility of sending the electronic document to the SRI')
    authorization = fields.Boolean('Authorized by SRI', copy=False, help='Selected indicates that the invoice is authorized by the SRI')
    received = fields.Boolean('Received by SRI', copy=False, help='Selected indicates that the invoice is received by the SRI')
    access_key = fields.Char('Access key', size=49, copy=False, help='Access code generated by the company to be validated')
    authorization_date = fields.Char('Authorization date', size=100, copy=False, help='Authorization date validated by SRI')
    authorization_number = fields.Char('N° authorization', size=49, copy=False, help='Authorization number validated by SRI')
    environment = fields.Char('Environment', size=50, copy=False)
    emission_code = fields.Char('Type the emssion', size=1, default='2', copy=False)
    message_state = fields.Char('Message Authorization', size=25, copy=False)
    line_info_ids = fields.One2many('additional.info', 'withholding_id', string='Information Additional Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    
    move_line_ids = fields.One2many('account.move.line', 'withholding_id', readonly=True, copy=False, ondelete='restrict')
    residual = fields.Monetary(string='Amount Due', compute='_compute_residual', store=True, help="Remaining amount due.")
    residual_signed = fields.Monetary(string='Amount Due in Invoice Currency', currency_field='currency_id',
        compute='_compute_residual', store=True, help="Remaining amount due in the currency of the invoice.")
    residual_company_signed = fields.Monetary(string='Amount Due in Company Currency', currency_field='company_currency_id',
        compute='_compute_residual', store=True, help="Remaining amount due in the currency of the company.")
    move_reconciled = fields.Boolean(compute="_compute_residual", readonly=True, store=True)
    attachment_number = fields.Integer(compute='_get_attachment_number', string="Number of Attachments")
    
    outstanding_credits_debits_widget = fields.Text(compute='_get_outstanding_info_JSON', groups="account.group_account_invoice")
    invoices_widget = fields.Text(compute='_get_invoice_info_JSON', groups="account.group_account_invoice")
    has_outstanding = fields.Boolean(compute='_get_outstanding_info_JSON', groups="account.group_account_invoice")
    invoice_move_line_ids = fields.Many2many('account.move.line', string='Invoice Move Lines', compute='_compute_payments', store=True)
    statement_tax_line_ids = fields.One2many('account.statement.tax', 'withhold_id',
        string='Statement', readonly=True, states={'draft': [('readonly', False)]}, copy=False)



    @api.one
    @api.constrains('number', 'authorization_id', 'type_document_id',  'company_id', 'type', 'state')
    def _check_number(self):
        if self.state != 'draft':
            domain = [('number', '=', self.number), ('company_id', '=', self.company_id.id), ('type_document_id', '=', self.type_document_id.id),
                      ('type', '=', self.type), ('authorization_id', '=', self.authorization_id.id), ('state', '!=', 'draft')]
            unique_number = self.search(domain)
            for x in unique_number:
                if x.id != self.id: raise UserError(_('Withholding Number must be unique per company!'))


    @api.model
    def create(self, vals):
        res = super(AccountWithholding, self).create(vals)
        for line in res.withholding_line_ids: line._onchange_tax_id()
        res._compute_total()
        return res


    def _get_aml_for_amount_residual(self):
        """ Get the aml to consider to compute the amount residual of invoices """
        self.ensure_one()
        return self.sudo().move_id.line_ids.filtered(lambda l: l.account_id == self.account_id)


    @api.one
    @api.depends('state', 'currency_id', 'withholding_line_ids.amount', 
                 'move_id.line_ids.amount_residual',
                 'move_id.line_ids.currency_id',
                 'move_line_ids.reconciled')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type == 'in_withholding' and -1 or 1
        for line in self._get_aml_for_amount_residual():
            residual_company_signed += line.amount_residual
            if line.currency_id == self.currency_id:
                residual += line.amount_residual_currency if line.currency_id else line.amount_residual
            else:
                from_currency = (line.currency_id and line.currency_id.with_context(date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                residual += from_currency.compute(line.amount_residual, self.currency_id)
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.move_reconciled = True
        else:
            self.move_reconciled = False


    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'approved' and self.residual > 0.0:
            invoices = [line.invoice_id.id for line in self.withholding_line_ids]
            domain = [('account_id', '=', self.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False),
                      ('invoice_id', 'in', invoices),
                      '|',
                        '&', ('amount_residual_currency', '!=', 0.0), ('currency_id','!=', None),
                        '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id','=', None), ('amount_residual', '!=', 0.0)]
            if self.type == 'out_withholding':
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'withholding_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(abs(line.amount_residual), self.currency_id)
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    if line.ref :
                        title = '%s : %s' % (line.move_id.name, line.ref)
                    else:
                        title = line.move_id.name
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'title': title,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True


    @api.model
    def _get_invoices_vals(self):
        if not self.invoice_move_line_ids:
            return []
        invoice_vals = []
        currency_id = self.currency_id
        for invoice in self.invoice_move_line_ids:
            invoice_currency_id = False
            if self.type == 'in_withholding':
                amount = sum(
                    [p.amount for p in invoice.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                amount_currency = sum([p.amount_currency for p in invoice.matched_credit_ids if
                                       p.credit_move_id in self.move_id.line_ids])
                if invoice.matched_credit_ids:
                    invoice_currency_id = all([p.currency_id == invoice.matched_credit_ids[0].currency_id for p in
                                               invoice.matched_credit_ids]) and invoice.matched_credit_ids[0].currency_id or False
            else:
                amount = sum([p.amount for p in invoice.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                amount_currency = sum(
                    [p.amount_currency for p in invoice.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                if invoice.matched_debit_ids:
                    invoice_currency_id = all([p.currency_id == invoice.matched_debit_ids[0].currency_id for p in
                                               invoice.matched_debit_ids]) and invoice.matched_debit_ids[
                                              0].currency_id or False
            # get the invoice value in withholding currency
            if invoice_currency_id and invoice_currency_id == self.currency_id:
                amount_to_show = amount_currency
            else:
                amount_to_show = invoice.company_id.currency_id.with_context(date=self.date_withholding).compute(amount, self.currency_id)
            if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                continue
            invoice_ref = invoice.move_id.name
            if invoice.move_id.ref:
                invoice_ref += ' (' + invoice.move_id.ref + ')'
            invoice_vals.append({
                'title': '%s %s' % (_('Invoice'), invoice.date),
                'name': invoice.name,
                'journal_name': invoice.journal_id.name,
                'amount': amount_to_show,
                'currency': currency_id.symbol,
                'digits': [69, currency_id.decimal_places],
                'position': currency_id.position,
                'date': invoice.date,
                'payment_id': invoice.id,
                'account_payment_id': invoice.payment_id.id,
                'invoice_id': invoice.invoice_id.id,
                'move_id': invoice.move_id.id,
                'ref': invoice_ref,
            })
        return invoice_vals


    @api.depends('state', 'authorization_id')
    def _get_sequence_prefix(self):
        for withholding in self:
            if withholding.authorization_id:
                withholding.sequence_number_next_prefix = '%s-%s-' % (withholding.authorization_id.entity, withholding.authorization_id.issue)
                withholding.comment = withholding.authorization_id.comment
                lines_info = []
                for line in withholding.authorization_id.line_info_ids:
                    lines_info.append((0, 0, {
                        'sequence': line.sequence,
                        'name': line.name,
                        'value_tag': line.value_tag,
                    }))
                withholding.line_info_ids = lines_info
            else:
                withholding.sequence_number_next_prefix = '000-000-'


    @api.depends('state', 'authorization_id')
    def _get_sequence_number_next(self):
        for withholding in self:
            if withholding.state not in ['draft']:
                if withholding.number: withholding.sequence_number_next = '%s' % withholding.number
            else:
                if not withholding.number:
                    withholding.sequence_number_next = '000000000'
                else:
                    if len(withholding.number) < 9:
                        withholding.number = '%%0%sd' % 9 % int(withholding.internal_number)
                    withholding.sequence_number_next = withholding.number


    @api.onchange('type_document_id', 'is_electronic', 'partner_id')
    def _onchange_is_electronic(self):
        res = {'domain': {}}
        values = {}
        domain = [('type_document_id', '=', self.type_document_id.id), ('is_electronic', '=', self.is_electronic), ('company_id', '=', self.env.user.company_id.id)]
        domain += [('type', '=', 'external' if self.type in ['in_withholding'] else 'internal')]
        if self.type == 'in_withholding': 
            domain += [('partner_id', '=', self.partner_id.id)]
            self.received = True if self.is_electronic else False
            self.authorization = True if self.is_electronic else False
            
            if self.partner_id:
                rec_account = self.partner_id.property_account_receivable_id
                pay_account = self.partner_id.property_account_payable_id
                if not rec_account and not pay_account:
                    action = self.env.ref('account.action_account_config')
                    msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                    raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
                self.account_id = rec_account.id
            
        user = self.env.user
        if len(user.authorization_ids) > 1:
            ids = user.authorization_ids.ids
            domain += [('id', 'in', ids)]
        if not self.authorization_id:
            auth = self._get_authorization(domain)
            if auth: values['authorization_id'] = auth.id
        res['domain'] = {'authorization_id': domain}
        self.update(values)
        return res


    @api.onchange('number')
    def _onchange_number(self):
        number = '%%0%sd' % 9 % 0
        if 'default_number' in self._context:
            self.number = int(self._context.get('default_number'))
        if self.number:
            number = '%%0%sd' % 9 % int(self.number)
        self.number = number


    def _get_authorization(self, domain):
        auth = self.env['account.authorization'].search(domain, limit=1, order="id asc")
        #if not auth: raise UserError(_('Does not have physical or electronic authorizations, create a new physical or electronic authorization'))
        return auth


    @api.multi
    def _set_sequence_next(self):
        if self.manual_sequence or not self.sequence_number_next:
            return False
        self.authorization_id._set_sequence_next("account_withholding", "('draft', 'approved', 'cancel')")


    @api.multi
    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online withholding for portal users. """
        self.ensure_one()
        user, record = self.env.user, self
        if access_uid:
            user = self.env['res.users'].sudo().browse(access_uid)
            record = self.sudo(user)

        if user.share or self.env.context.get('force_website'):
            try:
                record.check_access_rule('read')
            except exceptions.AccessError:
                if self.env.context.get('force_website'):
                    return {
                        'type': 'ir.actions.act_url',
                        'url': '/my/withholdings/%s' % self.id,
                        'target': 'self',
                        'res_id': self.id,
                    }
                else:
                    pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/withholdings/%s?access_token=%s' % (self.id, self.access_token),
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(AccountWithholding, self).get_access_action(access_uid)


    @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if not credit_aml.currency_id and self.currency_id != self.company_id.currency_id:
            credit_aml.with_context(allow_amount_currency=True, check_move_validity=False).write({
                'amount_currency': self.company_id.currency_id.with_context(date=credit_aml.date).compute(credit_aml.balance, self.currency_id),
                'currency_id': self.currency_id.id})
        if credit_aml.invoice_id:
            credit_aml.invoice_id.write({'withholding_id': self.id})
        return self.register_payment(credit_aml)


    @api.multi
    def _get_aml_for_register_payment(self):
        """ Get the aml to consider to reconcile in register invoice """
        self.ensure_one()
        return self.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))


    @api.multi
    def register_payment(self, invoice_line, writeoff_acc_id=False, writeoff_journal_id=False):
        """ Reconcile payable/receivable lines from the invoice with withholding_line """
        line_to_reconcile = self.env['account.move.line']
        for withhold in self:
            line_to_reconcile += withhold._get_aml_for_register_payment()
        return (line_to_reconcile + invoice_line).reconcile(writeoff_acc_id, writeoff_journal_id)


    def get_mail_url(self):
        return self.get_share_url()


    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        return  self.type == 'out_withholding' and self.state == 'draft' and self.type_document_id.name or \
                self.type == 'out_withholding' and self.state in ('approved') and _('%s - %s') % (self.type_document_id.name, self.number)


    @api.multi
    def action_withholding_sent(self):
        """ Open a window to compose an email, with the edi withholding template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('oe_account.mail_template_data_notification_email_account_withholding', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.withholding',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="account.mail_template_data_notification_email_account_invoice",
            force_email=True
        )
        self.sent = True
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
    def button_journal_entries(self):
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('withholding_id', 'in', self.ids)],
        }


    @api.multi
    def action_withholding_cancel(self):
        if self.filtered(lambda withh: withh.state not in ['draft', 'approved']):
            raise UserError(_('Withholding must be in draft or approved state in order to be cancelled.'))
        self.move_id = False
        for move in self.move_line_ids.mapped('move_id'):
            move.line_ids.remove_move_reconcile()
            move.button_cancel()
            move.unlink()  
        invoices_name = set(self.withholding_line_ids.mapped('tmpl_invoice_number'))
        self.state = 'cancel'
        if len(invoices_name):
            domain = [('name', 'in', list(invoices_name)), ('partner_id', '=', self.partner_id.id)]
            for invoice in self.env['account.invoice'].search(domain):
                invoice.write({'withholding_id': False, 'details_tax': False if invoice.details_tax else True})
                invoice._compute_residual()
        return True


    @api.multi
    def action_withholding_draft(self):
        if self.filtered(lambda withh: withh.state not in ['approved', 'cancel']):
            raise UserError(_('Withholding must be in cancel in order to be draft.'))
        vals = {'state': 'draft'}
        if not self.received and not self.manual_sequence:
            vals.update({'number': '000000000', 'internal_number': 0})
        self.write(vals)
        if not self.manual_sequence:
            sequence_id = self.authorization_id.sequence_id._get_current_sequence()
            self.sequence_number_next = '%%0%sd' % sequence_id.padding % sequence_id.number_next_actual
        invoices_name = set(self.withholding_line_ids.mapped('tmpl_invoice_number'))
        if len(invoices_name):
            domain = [('name', 'in', list(invoices_name)), ('partner_id', '=', self.partner_id.id)]
            for invoice in self.env['account.invoice'].search(domain):
                invoice.write({'details_tax': False if invoice.details_tax else True})
                invoice._compute_residual()
        return True


    @api.multi
    def action_withholding_approved(self):
        to_open_withholdings = self.filtered(lambda withh: withh.state != 'open')
        if to_open_withholdings.filtered(lambda withh: withh.state != 'draft'):
            raise UserError(_('Withholding must be in draft state in order to validate it.'))
        if not to_open_withholdings.date_withholding: to_open_withholdings.date_withholding = fields.Date.context_today(self)
        to_open_withholdings._validate_withholding()
        return True


    def _generate_key_access(self):
        if self.is_electronic and self.type_document_id.code_doc_xml and (not\
            self.access_key or not self.received or not self.authorization):
            access_key = self.authorization_id.generation_access_key(self.name, self.type_document_id, self.date_withholding)
        else:
            access_key = self.access_key
        return access_key


    def _get_sequence(self):
        padding = 9
        if not self.manual_sequence:
            if not self.authorization_id.sequence_id and self.authorization_id.is_electronic and self.authorization_id.type == 'internal':
                raise UserError(_('The authorizations do not have a sequence!'))
            sequence_id = self.authorization_id.sequence_id._get_current_sequence()
            padding = sequence_id and sequence_id.padding
            if self.number == '000000000' or not self.number:
                name_old = self.sequence_number_next_prefix + self.sequence_number_next
                if name_old != self.name or self.number == '000000000':
                    self.internal_number = sequence_id.number_next_actual
            else:
                self.internal_number = int(self.number)
        else:
            if self.number == '000000000':
                raise UserError(_('Enter the document number!'))
            self.internal_number = int(self.number)
        self.sequence_number_next = '%%0%sd' % padding % self.internal_number
        self.number = self.sequence_number_next
        name = '%s%s' % (self.sequence_number_next_prefix, self.number)
        self.name = name

    @api.multi
    def action_create_statement_tax(self):
        obj_statement = self.env['account.statement.tax']
        for withhold in self:
            statement_ids = dict()
            withhold.statement_tax_line_ids.unlink()
            for tax_line in withhold.withholding_line_ids:
                tax_id = tax_line.tax_id
                for tag_id in tax_id.tag_ids.filtered(lambda t: 'withholding' in t.document_type):
                    key = '%s-%s' % (tax_id.id, tag_id.name)
                    if key not in statement_ids:
                        statement_ids[key] = {
                            'withhold_id': withhold.id,
                            'form_id': tag_id.form_id and tag_id.form_id.id or False,
                            'name': tag_id.name,
                            'tax_group_id': tax_id.tax_group_id and tax_id.tax_group_id.id,
                            'base': 0.0,
                            'percentage': abs(tax_line.amount_tax),
                            'amount': 0.0
                        }
                    statement_ids[key]['base'] += tax_line.amount_base
                    statement_ids[key]['amount'] += tax_line.amount
            
            withholding_line_ids = withhold.withholding_line_ids.sorted(lambda x: x.amount)
            for line in withholding_line_ids:
                statement_line_ids = dict()
                line.statement_tax_line_ids.unlink()
                for tag_id in line.tax_id.tag_ids.filtered(lambda t: 'withholding' in t.document_type):
                    key = '%s-%s' % (line.tax_id.id, tag_id.name)
                    form_dict = statement_ids[key]
                    if key not in statement_line_ids:
                        statement_line_ids[key] = {
                        'withhold_line_id': line.id,
                        'form_id': form_dict['form_id'],
                        'name': form_dict['name'],
                        'tax_group_id': form_dict['tax_group_id'],
                        'base': 0.0,
                        'percentage': form_dict['percentage'],
                        'amount': 0.0,  
                        }
                    statement_line_ids[key]['base'] += line.amount_base
                    statement_line_ids[key]['amount'] += line.amount

                for key, vals in statement_line_ids.items():
                    obj_statement.create(vals)
            for key, vals in statement_ids.items():
                obj_statement.create(vals)

    def _validate_withholding(self):
        self.withholding_validate()
        self._get_sequence()
        move_wh = self.action_move_create()
        self.action_create_statement_tax()
        sequence_count = defaultdict(int)
        for tax_line in self.mapped('withholding_line_ids').filtered(lambda l: l.tax_id):
            sequence_count[tax_line.tax_id] += 1
        for tax, count in sequence_count.items():
            tax._increase_rank('sequence', count)
        self.write({'state': 'approved', 'access_key': self._generate_key_access()})
        authorization = self.is_electronic and self.access_key or self.authorization_id.name
        move_wh.write({
            'type_document_id': self.type_document_id and self.type_document_id.id or False,
            'authorization_id': authorization or False,
            'origin': self.name or False,
        })
        invoice_ids = self.withholding_line_ids.filtered(lambda l: l.invoice_id).mapped('invoice_id')
        for invoice_id in invoice_ids:
            invoice_id.with_context(refresh=True).action_payment_methods()
            invoice_id.write({'details_tax': False if invoice_id.details_tax else True})
        moves_in = invoice_ids.mapped('move_id').ids
        if not self.concile_invoice_withholing(moves_in, move_wh):
            raise UserError(_('Can not reconcile the invoice and withholding'))
        return True

    
    def withholding_validate(self):
        for withholding in self.filtered(lambda withholding: withholding.partner_id not in withholding.message_partner_ids):
            withholding.message_subscribe([withholding.partner_id.id])
            if withholding.reference:
                if self.search([('type', '=', withholding.type), ('reference', '=', withholding.reference), ('number', '=', withholding.number), ('company_id', '=', withholding.company_id.id), ('id', '!=', withholding.id)]):
                    raise UserError(_('Duplicated vendor reference detected. You probably encoded twice the same withholding.'))
        return True


    @api.multi
    def action_move_create(self):
        """ Creates withholding related analytics and financial move lines """
        account_move = self.env['account.move']
        
        for wh in self:
            ctx = dict(self._context, lang=wh.partner_id.lang)
            wml = wh.withholding_line_move_line_get()
            #if self.amount_refund > 0.0:
            #    account_id = wml[0]['account_id']
            #    wml.append(wh.withholding_line_move_refund(account_id))
            wml.append(wh.withholding_line_move_get())
            lines = [(0, 0, x) for x in wml]
            date = wh.date_withholding or wh.date_invoice
            move_vals = {
                'ref': wh.reference,
                'line_ids': lines,
                'journal_id': wh.journal_id.id,
                'date': date,
                'narration': wh.comment,
            }
            ctx['company_id'] = wh.company_id.id
            ctx['withholding'] = wh
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass withholding in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the withholding point to that move
            vals = {
                'move_id': move.id,
                'date_withholding': date,
                'move_name': move.name,
            }
            wh.with_context(ctx).write(vals)
        return move

    @api.model
    def withholding_line_move_refund(self, account_id):
        move_line_dict = {
            'date_maturity': self.date_withholding,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'name': _('Guarantee fund %s') % self.name.split('\n')[0][:64],
            'debit': self.type != 'in_withholding' and self.amount_refund or 0.0,
            'credit': self.type == 'in_withholding' and self.amount_refund or 0.0,
            'account_id': account_id,
            'analytic_line_ids': [],
            'amount_currency': 0,
            'currency_id': False,
            'quantity': 1,
            'product_id': False,
            'product_uom_id': False,
            'analytic_account_id': False,
            'withholding_id': self.id,
            'tax_ids': [],
            'tax_line_id': False,
            'analytic_tag_ids': []
        }
        return move_line_dict

    @api.model
    def withholding_line_move_get(self):
        move_line_dict = {
            'date_maturity': self.date_withholding,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'name': self.name.split('\n')[0][:64],
            'debit': self.type != 'in_withholding' and self.amount_total or 0.0,
            'credit': self.type == 'in_withholding' and self.amount_total or 0.0,
            'account_id': self.account_id.id,
            'analytic_line_ids': [],
            'amount_currency': 0,
            'currency_id': False,
            'quantity': 1,
            'product_id': False,
            'product_uom_id': False,
            'analytic_account_id': False,
            'withholding_id': self.id,
            'tax_ids': [],
            'tax_line_id': False,
            'analytic_tag_ids': []
        }
        return move_line_dict
        

    @api.model
    def withholding_line_move_line_get(self):
        res = []
        for line in self.withholding_line_ids:
            analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
            move_line_dict = {
                'date_maturity': self.date_withholding,
                'partner_id': self.partner_id and self.partner_id.id or False,
                'name': line.tax_id and line.tax_id.name or line.description,
                'debit': self.type == 'in_withholding' and line.amount or 0.0,
                'credit': self.type != 'in_withholding' and line.amount or 0.0,
                'account_id': line.account_id.id,
                'analytic_line_ids': [],
                'amount_currency': 0,
                'currency_id': False,
                'quantity': 1,
                'product_id': False,
                'product_uom_id': False,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'withholding_id': self.id,
                'tax_ids': line.tax_id and [(4, line.tax_id.id, None)] or False,
                'tax_line_id':  line.tax_id and line.tax_id.id or False,
                'analytic_tag_ids': analytic_tag_ids,
                'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
            }
            res.append(move_line_dict)
        return res


    def concile_invoice_withholing(self, moves_in, move_wh, writeoff_acc_id=False, writeoff_journal_id=False):
        for move in self.env['account.move'].browse(moves_in):
            line_inv_to_reconcile = move.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        line_wh_to_reconcile = move_wh.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        return (line_inv_to_reconcile + line_wh_to_reconcile).reconcile(writeoff_acc_id, writeoff_journal_id)


    @api.multi
    def unlink(self):
        for withholding in self:
            if withholding.state in ('approved', 'cancel'):
                raise UserError(_('You cannot delete an withholding which is not draft.'))
            elif withholding.type == 'out_withholding' and withholding.authorization:
                raise UserError(_('You cannot delete an withholding after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
            invoices_name = set(withholding.withholding_line_ids.mapped('tmpl_invoice_number'))
            if len(invoices_name):
                invoices = self.env['account.invoice'].search([('name', 'in', list(invoices_name)), ('partner_id', '=', withholding.partner_id.id)])
                invoices.write({'withholding_id': False})
        return super(AccountWithholding, self).unlink()


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
            [('res_model', '=', 'account.withholding'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attach_data = dict((res['res_id'], res['res_id_count']) for res in read_group_res)
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)


class AccountWithholdingLine(models.Model):
    _name = "account.withholding.line"
    _description = "Withholding Line"
    _order = "withholding_id,sequence,id"

    
    name = fields.Selection([('renta_iva', 'IVA'),
        ('renta', 'RENTA'),
        ('isd', 'ISD')], string='type', default='renta', required=True, copy=True, help='Select the type of withhold to add in the lines')
    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying the withholding.")
    description = fields.Text(string='Description')
    withholding_id = fields.Many2one('account.withholding', string='Withhold Reference', ondelete='cascade', index=True)
    withholding_type = fields.Selection(related='withholding_id.type', readonly=True)
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    partner_id = fields.Many2one('res.partner', string='Partner',
        related='withholding_id.partner_id', store=True, readonly=True, related_sudo=False)
    type_withhold = fields.Selection(selection=[('fixed', 'Fixed'), ('percent', 'Percentage')],
        string='Type Withhold', default='percent', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax to Withhold')
    tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")
    account_id = fields.Many2one('account.account', 'Account', required=True)
    company_id = fields.Many2one('res.company', string='Company', related='withholding_id.company_id', store=True, readonly=True, related_sudo=False)
    currency_id = fields.Many2one('res.currency', related='withholding_id.currency_id', store=True, related_sudo=False)
    company_currency_id = fields.Many2one('res.currency', related='withholding_id.company_currency_id', readonly=True, related_sudo=False)
    amount_tax = fields.Float(string='Withhold to', required=True, default=0.0)
    amount_base = fields.Monetary(string='Base Amount', required=True, default=0.0, help="Total amount with taxes")
    amount_refund = fields.Monetary(string='Refund Amount', required=True, default=0.0, help='Refund amount')
    amount = fields.Monetary(string='Amount', required=True, default=0.0, help="Total amount with taxes")
    livelihood_id = fields.Many2one('account.type.document', string='Livelihood Code', copy=False, change_default=True, required=True)
    tmpl_invoice_number = fields.Char(string='Number', size=17, default='000-000-000000000', help='Number referring to the document to withhold')
    tmpl_invoice_date = fields.Date('Date emission', copy=False, help='Date emission referring to the document to withhold')
    invoice_id = fields.Many2one('account.invoice', 'Invoice', copy=False)
    statement_tax_line_ids = fields.One2many('account.statement.tax', 'withhold_line_id',
        string='Statement', readonly=True, copy=False)


    @api.onchange('tmpl_invoice_number')
    def onchange_tmpl_invoice_number(self):
        #%03d-%03d-%09d
        if self.tmpl_invoice_number:
            if not re.match('^\d{3}-\d{3}-\d{9}$', self.tmpl_invoice_number):
                raise UserError(_('Enter the invoice correctly Example: 001-001-000000025'))
            if self.tmpl_invoice_number and not self.invoice_id:
                invoice = self.env['account.invoice'].search([('name', '=', self.tmpl_invoice_number),('partner_id', '=', self.partner_id.id)], limit=1)
                self.invoice_id = invoice.id if invoice else False


    @api.onchange('name', 'invoice_id')
    def _onchange_name(self):
        part = self.withholding_id.partner_id
        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner!'),
                }
            return {'warning': warning}

        res = {}
        amount = 0.0
        type_group_id = self.env['account.tax.group'].search([('type', '=', self.name)], limit=1).id
        domain = {'tax_id': [('tax_group_id', '=', type_group_id)]}
        if domain:
            res['domain'] = domain
        if self.invoice_id:
            if self.name == 'renta_iva':
                amount = self.invoice_id.amount_tax
            elif self.name == 'renta':
                amount = self.invoice_id.amount_subtotal
        self.amount_base = amount
        return res
        

    @api.onchange('name', 'tax_id')
    def _onchange_tax(self):
        res = {'domain': {}}
        self.account_id = self.tax_id.account_id.id
        self.amount_tax = self.tax_id.amount
        self.tax_tag_ids = self.tax_id.mapped('tag_ids').filtered(lambda l: 'withholding' in l.document_type)
        domain = [('tax_group_id.type', '=', self.name)]
        if self.withholding_type == 'in_withholding':
            domain.extend([('type_tax_use','=','sale'),('amount', '<=', 0)])
        else:
            domain.extend([('type_tax_use','=','purchase'),('amount', '<=', 0)])
        res['domain']['tax_id'] = domain
        return res


    @api.onchange('amount_tax', 'amount_base', 'amount',
        'type_withhold', 'amount_refund')
    def _onchange_tax_id(self):
        if self.type_withhold =='percent':
            #if not self.tax_id.tax_adjustment:
            self.amount = abs(float_round(self.amount_tax * self.amount_base / 100.0, 2)) - self.amount_refund
        else:
            if self.withholding_id.document_type and 'withhold' in self.withholding_id.document_type:
                self.amount = self.amount_base - self.amount_tax
                if self.amount_refund > 0.0:
                    self.amount -= self.amount_refund
            else:
                self.amount = self.amount_tax
                if self.amount_refund > 0.0:
                    self.amount -= self.amount_refund


    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.tmpl_invoice_date = self.invoice_id.date_invoice
            self.tmpl_invoice_number = self.invoice_id.name
            self.livelihood_id = self.invoice_id.type_document_id.id
            if self.withholding_id.type == 'in_withholding':
                self.amount_base = self.invoice_id.amount_subtotal if self.name == 'renta' else self.invoice_id.total_tax
            else:
                for x in self.invoice_id.tax_line_ids:
                    if x.tax_id.tax_group_id.type in ['renta', 'renta_iva']:
                        self.account_id = x.account_id.id
                        self.tax_id = x.tax_id.id
                        self.amount_tax = x.tax_id.amount
                        self.amount_base = x.base
                        self.amount = abs(x.amount_total)


    @api.multi
    def unlink(self):
        if self.filtered(lambda r: r.withholding_id and r.withholding_id.state != 'draft'):
            raise UserError(_('You can only delete an withholding line if the withholding is in draft state.'))
        return super(AccountWithholdingLine, self).unlink()
    
