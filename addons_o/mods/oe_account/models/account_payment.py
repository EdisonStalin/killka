# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import models, api, fields, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


# Since invoice amounts are unsigned, this is how we know if money comes in or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}

class AccountCardType(models.Model):
    _name = "account.card.type"
    _description = "Card type"
    
    name = fields.Char(string='Name', size=150, required=True)
    code = fields.Char(string='Card Code', size=2, required=True)
    active = fields.Boolean(default=True, help="Set active to false to hide the type document without removing it")


    @api.multi
    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, '%s - %s' % (record.code, record.name)))
        return res


    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', '=' + operator, name + '%')]
        recs = self.search(expression.AND([domain, args]), limit=limit)
        return recs.name_get()


class AccountMethodPayment(models.Model):
    _name = "account.method.payment"
    _description = "Register method of payment"
    
    name = fields.Char(string='Method', size=150, required=True)
    code = fields.Char(string='Method Code', size=2, required=True)
    sequence = fields.Integer(required=True, default=10)
    active = fields.Boolean(default=True, help="Set active to false to hide the type document without removing it")


    @api.multi
    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, '%s - %s' % (record.code, record.name)))
        return res


    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', '=' + operator, name + '%')]
        recs = self.search(expression.AND([domain, args]), limit=limit)
        return recs.name_get()

class AccountRegisterPayments(models.TransientModel):
    _inherit = 'account.register.payments'

    # Note: a check_number == 0 means that it will be attributed when the check is printed
    check_number = fields.Integer(string="Check Number", readonly=False, copy=False, default=0,
        help="Number of the check corresponding to this payment. If your pre-printed check are not already numbered, "
             "you can manage the numbering in the journal configuration page.")

    @api.onchange('payment_method_id')
    def _onchange_payment_method_id(self):
        if self.payment_method_code == 'check_printing':
            self.pay_to = '%s %s' % (self.partner_id.firstname, self.partner_id.lastname or '')
            self.pos_payment_date = self.payment_date
            self._onchange_amount()

class AccountAbstractPayment(models.AbstractModel):
    _inherit = 'account.abstract.payment'


    @api.depends('payment_line_ids.amount')
    def _compute_amount_values(self):
        for payment in self.filtered(lambda p: p.show_details):
            payment.amount_values = sum(line.amount for line in payment.payment_line_ids)
            payment.amount = payment.amount_values

    document_number = fields.Char(string='Document Number', size=250)
    is_advance = fields.Boolean(string='Advance?')
    show_details = fields.Boolean(related='journal_id.show_details')
    is_card = fields.Boolean(related='journal_id.is_card')
    method_id = fields.Many2one('account.method.payment', string='Payment Method', help='Choose the form of payment made by the client')
    conciliation_type = fields.Selection([('normal', 'Normal'), ('counterpart', 'Counterpart')], string='Conciliation Action', default='normal', required=True)
    amount = fields.Float(string='Payment Amount', required=True)
    pay_to = fields.Char(string='Pay to the order of', size=200, help='Name of the person who (Payable to the order of).')
    check_number = fields.Integer(string="Check Number", readonly=False, copy=False,
        help="The selected journal is configured to print check numbers. If your pre-printed check paper already has numbers "
             "or if the current numbering is wrong, you can change it in the journal configuration page.")
    pos_payment_date = fields.Date(string='Post Payment Date', copy=False)
    check_amount_in_words = fields.Char(string="Amount in Words")
    check_amount_in_words2 = fields.Char(string="Amount in Words", help='Optional line in case you lack space on the line of the amount in words.')
    check_manual_sequencing = fields.Boolean(related='journal_id.check_manual_sequencing', readonly=1)
    amount_values = fields.Float(compute='_compute_amount_values', store=True)
    payment_line_ids = fields.One2many('account.payment.line', 'payment_id', string='Pending values')
    line_extra_ids = fields.One2many('account.payment.line.extra', 'payment_id', string='Extra values')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    partner_bank_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account")
    user_id = fields.Many2one('res.users', string='Responsible',
        track_visibility='onchange', default=lambda self: self.env.user, copy=False)
    approved_id = fields.Many2one('res.users', string='Approved by',
        track_visibility='onchange', default=lambda self: self.env.user, copy=False)
    notes = fields.Text(string='Notes')
    
    @api.onchange('amount_values')
    def _onchange_amount(self):
        if self.show_details:
            self.amount += self.amount_values
            
    @api.onchange('is_advance')
    def _onchange_is_advance(self):
        if self.is_advance:
            self.conciliation_type = 'counterpart'
        else:
            self.conciliation_type = 'normal'

class AccountPaymentLineExtra(models.Model):
    _name = "account.payment.line.extra"
    _description = "Payment extra"
    
    
    name = fields.Char(string='Reference', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    description = fields.Char(string='Description', size=250)
    amount = fields.Float(string='Value', required=True, default=0.0, help='Referred value to calculate in the payment.')
    payment_id = fields.Many2one('account.payment', string='Payment', required=True)


class AccountPaymentLine(models.Model):
    _name = "account.payment.line"
    _description = "Payment details"
    _order = 'date asc'


    @api.depends('move_line_id')
    def _store_balance(self):
        for line in self:
            line.balance = abs(line.move_line_id.balance)
            line.amount_residual = abs(line.move_line_id.amount_residual)


    payment_id = fields.Many2one('account.payment', string='Payment', required=True)
    move_line_id = fields.Many2one('account.move.line', string='Journal Item', required=True)
    name = fields.Char(related='move_line_id.name')
    account_id = fields.Many2one('account.account', related='move_line_id.account_id')
    date_maturity = fields.Date(related='move_line_id.date_maturity')
    date = fields.Date(related='move_line_id.date')
    invoice_id = fields.Many2one('account.invoice', related='move_line_id.invoice_id')
    partner_id = fields.Many2one('res.partner', related='move_line_id.partner_id')
    amount_residual = fields.Monetary(compute='_store_balance', store=True)
    balance = fields.Monetary(compute='_store_balance', string='Amount', store=True)
    currency_id = fields.Many2one('res.currency', related='move_line_id.currency_id')
    amount = fields.Monetary(string='Payment Amount', required=True, default=0.0)


class AccountPayment(models.Model):
    _inherit = 'account.payment'


    check_number = fields.Integer(string="Check Number", readonly=False, copy=False,
        help="The selected journal is configured to print check numbers. If your pre-printed check paper already has numbers "
             "or if the current numbering is wrong, you can change it in the journal configuration page.")
    date_reconcile = fields.Date(string='Reconcile Date', readonly=True, states={'draft': [('readonly', False)]})
    destination_account_id = fields.Many2one('account.account', string='Destination Account', readonly=False, store=True, compute=False)


    @api.model
    def default_get(self, fields):
        rec = super(AccountPayment, self).default_get(fields)
        if 'conciliation_type' not in rec: rec['conciliation_type'] = 'normal'
        if 'method_id' not in rec:
            rec['method_id'] = self.env.ref('oe_account.payment_method_20').id
        rec.update({'communication': False})
        if 'active_model' in self._context:
            if self._context.get('active_model')=='account.invoice':
                active_ids = self._context.get('active_ids')
                invoices = self.env['account.invoice'].browse(active_ids)
                rec.update({
                    'document_number': ' '.join([ref for ref in invoices.mapped('name') if ref]),
            })
        return rec


    def _get_move_lines_extra(self):
        line_extra_ids = [(6, 0, [])]
        for line in self.journal_id.line_values_ids:
            line_extra_ids.append((0, 0, {
                'name': line.name,
                'account_id': line.account_id.id,
                'amount': 0.0,
            }))
        return line_extra_ids
    
    @api.onchange('is_advance')
    def _onchange_is_advance(self):
        if self.is_advance:
            self._set_account()

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        res = {'value': {}}
        if self.journal_id:
            self.method_id = self.journal_id.method_id.id
        if self.journal_id and self.is_card:
            res['value']['line_extra_ids'] = self._get_move_lines_extra()
        return res


    def _get_move_lines(self):
        payment_line_ids = [(6, 0, [])]   
        domain = [('partner_id','=',self.partner_id.id), ('account_id', '=', self.destination_account_id.id), ('reconciled', '=', False), '|',
                  ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0)]
        domain += [('credit', '>', 0), ('debit', '=', 0)] if self.partner_type=='supplier' else [('credit', '=', 0), ('debit', '>', 0)]
        move_line_ids = self.env['account.move.line'].search(domain)
        for line in move_line_ids:
            payment_line_ids.append((0, 0, {
                'move_line_id': line.id,
                'amount': 0.0,
            }))
        return payment_line_ids
    
    def _set_account(self):
        company_id = self.env.user.company_id
        if self.conciliation_type == 'normal':
            if self.invoice_ids:
                self.destination_account_id = self.invoice_ids[0].account_id.id
            elif self.payment_type == 'transfer':
                if not self.company_id.transfer_account_id.id:
                    raise UserError(_('Transfer account not defined on the company.'))
                self.destination_account_id = self.company_id.transfer_account_id.id
            elif self.partner_id:
                if self.partner_type == 'customer':
                    self.destination_account_id = self.partner_id.property_account_receivable_id.id
                else:
                    self.destination_account_id = self.partner_id.property_account_payable_id.id
            elif self.partner_type == 'customer':
                default_account = self.env['ir.property'].get('property_account_receivable_id', 'res.partner')
                self.destination_account_id = default_account and default_account.id or False
            elif self.partner_type == 'supplier':
                default_account = self.env['ir.property'].get('property_account_payable_id', 'res.partner')
                self.destination_account_id = default_account and default_account.id or False
        if not self.destination_account_id:
            self.destination_account_id = company_id.property_account_payable_id.id if self.partner_type == 'supplier'\
                else company_id.property_account_receivable_id.id

    @api.onchange('partner_id', 'partner_type')
    def _onchange_partner(self):
        res = {'value': {}}
        if not self.conciliation_type: self.conciliation_type = 'normal'
        if self.partner_id and self.show_details:
            res['value']['payment_line_ids'] = self._get_move_lines()
        return res


    @api.onchange('payment_method_id')
    def _onchange_payment_method_id(self):
        if self.payment_method_code == 'check_printing':
            self.pay_to = '%s %s' % (self.partner_id.firstname, self.partner_id.lastname or '')
            self.pos_payment_date = self.payment_date
            self._onchange_amount()


    def _review_text_amount(self):
        amount_words = self.currency_id.amount_to_text(self.amount)
        formatted = "%.{0}f".format(self.currency_id.decimal_places) % self.amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)
        if fractional_value:
            amount_words = ''.join(amount_words.replace(self.currency_id.currency_subunit_label, '/100'))
        if integer_value:
            amount_words = ''.join(amount_words.replace(self.currency_id.currency_unit_label, ''))
        return '%s ************' % amount_words.upper()


    @api.onchange('amount', 'payment_method_code', 'currency_id')
    def _onchange_amount(self):
        res = super(AccountPayment, self)._onchange_amount()
        if self.amount:
            amount_words = self._review_text_amount()
            self.check_amount_in_words = amount_words[0: 50]
            self.check_amount_in_words2 = amount_words[50:]
        return res


    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            if rec.show_details:
                rec.payment_line_ids.filtered(lambda l: l.amount == 0.0).unlink()
                rec.invoice_ids += rec.payment_line_ids.mapped('invoice_id')

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            ref_xml_payment = False
            if rec.payment_type == 'transfer':
                if rec.payment_method_id.payment_type == 'outbound':
                    sequence_code = 'account.payment.supplier.invoice'
                    ref_xml_payment = 'sequence_payment_supplier_invoice'
                elif rec.payment_method_id.payment_type == 'inbound':
                    sequence_code = 'account.payment.customer.invoice'
                    ref_xml_payment = 'sequence_payment_customer_invoice'
                else:
                    sequence_code = 'account.payment.transfer'
                    ref_xml_payment = 'sequence_payment_transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                        ref_xml_payment = 'sequence_payment_customer_invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                        ref_xml_payment = 'sequence_payment_customer_refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                        ref_xml_payment = 'sequence_payment_supplier_refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
                        ref_xml_payment = 'sequence_payment_supplier_invoice'
            
            force_company = self.env.user.company_id.id
            if len(self.env.user.company_ids) > 1:
                force_company = False
                company_id = self.env.user.company_id.id
                sequence_obj = self.env['ir.sequence'].sudo()
                seq_id = sequence_obj.search([('code', '=', sequence_code), ('company_id', '=', company_id)], order='company_id')
                if not seq_id:
                    sequence_default = self.env.ref('account.'+ref_xml_payment).read()[0]
                    for x in ['id', 'date_range_ids', 'create_uid', 'create_date', 'write_uid', 'write_date']:
                        del sequence_default[x]
                    sequence_default['company_id'] = company_id
                    sequence_default['implementation'] = 'no_gap'
                    sequence_default['number_next_actual'] = 1
                    seq_id = sequence_obj.create(sequence_default)
                if not seq_id:
                    raise UserError(_("No ir.sequence has been found for code '%s'. Please make sure a sequence is set for current company.") % sequence_code)
            if not rec.name:
                rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date, force_company=force_company).next_by_code(sequence_code)
            if not rec.name and rec.payment_type != 'transfer':
                raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            if not rec.destination_account_id:
                rec._compute_destination_account_id()
            move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({'state': 'posted', 'move_name': move.name})
        return True

    def _get_move_vals(self, journal=None):
        vals = super(AccountPayment, self)._get_move_vals(journal)
        vals.update({'ref': '%s %s' % (self.communication or '', self.document_number or '')})
        return vals

    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

        move = self.env['account.move'].create(self._get_move_vals())

        #Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        if self.is_card:
            for line in self.line_extra_ids:
                amount_ex = -line.amount if self.partner_type == 'customer' else line.amount
                debit_ex, credit_ex, amount_currency_ex, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(amount_ex, self.currency_id, self.company_id.currency_id)
                liquidity_aml_dict = self._get_shared_move_line_vals(credit_ex, debit_ex, -amount_currency_ex, move.id, False)
                liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-line.amount))
                liquidity_aml_dict.update({'name': line.name, 'account_id': line.account_id.id})
                aml_obj.create(liquidity_aml_dict)
                debit -= debit_ex
                credit -= credit_ex
                amount -= amount_ex

        #Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(self.payment_difference, self.currency_id, self.company_id.currency_id)
            writeoff_line['name'] = self.writeoff_label
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo

        #Write counterpart lines
        if not self.currency_id.is_zero(self.amount):
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
            aml_obj.create(liquidity_aml_dict)

        #validate the payment
        move.post()

        #reconcile the invoice receivable/payable line(s) with the payment
        self.invoice_ids.register_payment(counterpart_aml)

        return move


    def _get_move_line_extra(self, line, debit, credit, move_id):
        credit -= line.amount
        vals = {
            'partner_id': self.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
            'move_id': move_id.id,
            'debit': debit,
            'credit': credit,
            'amount_currency': False,
            'payment_id': self.id,
            'journal_id': self.journal_id.id,
        }
        return vals
        

    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        return _('Check - %s') % (self.name)


    @api.multi
    def print_checks(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        # Since this method can be called via a client_action_multi, we need to make sure the received records are what we expect
        self = self.filtered(lambda r: r.payment_method_id.code == 'check_printing' and r.state in ['posted','reconciled'])

        if len(self) == 0:
            raise UserError(_("Payments to print as a checks must have 'Check' selected as payment method and "
                              "not have already been reconciled"))
        if any(payment.journal_id != self[0].journal_id for payment in self):
            raise UserError(_("In order to print multiple checks at once, they must belong to the same bank journal."))

        if not self[0].journal_id.check_manual_sequencing:
            # The wizard asks for the number printed on the first pre-printed check
            # so payments are attributed the number of the check the'll be printed on.
            last_printed_check = self.search([
                ('journal_id', '=', self[0].journal_id.id),
                ('check_number', '!=', 0)], order="check_number desc", limit=1)
            next_check_number = self.check_number or 1
            return {
                'name': _('Print Pre-numbered Checks'),
                'type': 'ir.actions.act_window',
                'res_model': 'print.prenumbered.checks',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'payment_ids': self.ids,
                    'default_next_check_number': next_check_number,
                }
            }
        else:
            self.filtered(lambda r: r.state == 'draft').post()
            return self.do_print_checks()


    @api.multi
    def do_print_checks(self):
        action = self.env.ref('oe_account_report.account_check_bank')
        action.paperformat_id = self.journal_id.bank_id.paperformat_id
        return action.report_action(self)


    @api.multi
    def unlink(self):
        if any(bool(rec.move_line_ids) for rec in self):
            raise UserError(_("You can not delete a payment that is already posted"))
        return models.Model.unlink(self)

    @api.multi
    def write(self, vals):
        return super(AccountPayment, self).write(vals)

class AccountMoveMethodPayment(models.Model):
    _name = "account.move.method.payment"
    _description = "Method Payment on Documents"
    _rec_name = 'method_id'
    _order = "sequence,id"


    @api.model
    def _get_default_currency(self):
        ''' Get the default currency from either the journal, either the default journal's company. '''
        return self.journal_id.currency_id or self.journal_id.company_id.currency_id 


    sequence = fields.Integer(required=True, default=10)
    method_id = fields.Many2one('account.method.payment', string='Way to pay', required=True, help='Choose the form of payment made by the customer')
    days = fields.Integer(string='Number of Days', required=True, default=0)
    date_due = fields.Date(string='Due Date', index=True, copy=False,
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. The Payment terms may compute several due dates, for example 50% "
             "now and 50% in one month, but if you want to force a due date, make sure that the payment "
             "term is not set on the invoice. If you keep the Payment terms and the due date empty, it "
             "means direct payment.")
    value = fields.Selection([
            ('balance', 'Balance'),
            ('percent', 'Percent'),
            ('fixed', 'Fixed Amount')
        ], string='Type', required=True, default='fixed',
        help="Select here the kind of valuation related to this payment terms line.")
    value_amount = fields.Float(string='Value', digits=dp.get_precision('Payment Terms'), default=0.0, help="For percent enter a ratio between 0-100.")
    amount = fields.Monetary(string='Amount Total to Pay', default=0.0, help='Amount distributed in the form of payment indicated by SRI')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    invoice_id = fields.Many2one('account.invoice', string='Document Reference', ondelete='cascade', index=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    currency_id = fields.Many2one('res.currency', store=True, required=True, string='Currency', default=_get_default_currency)


    @api.model
    def default_get(self, default_fields):
        res = super(AccountMoveMethodPayment, self).default_get(default_fields)
        if 'method_id' not in res:
            res['method_id'] = self.env.ref('oe_account.payment_method_20').id
        if 'payment_term_id' not in res:
            res['payment_term_id'] = self.env.ref('account.account_payment_term_immediate').id
        return res


    def name_get(self):
        name_list = []
        for record in self:
            name = '(%s) %s' % (record.amount, record.method_id.name)
            name_list += [(record.id, name)]
        return name_list


    @api.onchange('days', 'date_due')
    def _onchange_date_due(self):
        if self.invoice_id.date_invoice:
            next_date = fields.Date.from_string(self.invoice_id.date_invoice)
            next_date += relativedelta(days=self.days)
            self.date_due = next_date


    @api.onchange('value', 'value_amount')
    def _onchange_amount(self):
        if self.invoice_id:
            currency = self.env.user.company_id.currency_id
            value = self.invoice_id.total
            sign = value < 0 and -1 or 1
            if self.value == 'fixed':
                amt = sign * currency.round(self.value_amount)
            elif self.value == 'percent':
                amt = currency.round(value * (self.value_amount / 100.0))
            elif self.value == 'balance':
                amt = currency.round(value)
            self.amount = amt
