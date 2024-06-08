# -*- coding: utf-8 -*-

import copy

from odoo import models, api, fields, _
from odoo.tools import float_round, float_repr, pycompat
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"


    @api.depends('move_line_ids')
    def _compute_move_payment(self):
        for line in self:
            line.move_debit_ids = line.move_line_ids.filtered(lambda l: l.payment_id and l.debit > 0.0 and l.credit == 0.0)
            line.move_credit_ids = line.move_line_ids.filtered(lambda l: l.payment_id and l.credit > 0.0 and l.debit == 0.0)
    

    count_no_payment = fields.Integer(string='Payments not Reconciled', default=0)
    move_debit_ids = fields.One2many('account.move.line', compute='_compute_move_payment', string='Movement of debit payments')
    move_credit_ids = fields.One2many('account.move.line', compute='_compute_move_payment', string='Movement of credit payments')
    date_close = fields.Date(required=True, states={'confirm': [('readonly', True)]}, index=True, copy=False, default=fields.Date.context_today)

    @api.multi
    def button_journal_items(self):
        action = self.env.ref('oe_account.action_account_moves_reconciled').read()[0]
        move_line_ids = self.move_debit_ids + self.move_credit_ids
        if len(move_line_ids) >= 1:
            action['domain'] = [('id', 'in', move_line_ids.ids)]
        else:
            action['domain'] = [('journal_id','=',self.journal_id.id), ('date','<=',self.date_close), ('date','>=',self.date)]
        return action

    def _get_move_lines(self):
        domain_pay = [('journal_id','=',self.journal_id.id), ('payment_date','>=',self.date), ('payment_date','<=',self.date_close),('state','=','posted')]
        payment_ids = self.env['account.payment'].search(domain_pay)
        domain_move = [('journal_id','=',self.journal_id.id), ('payment_id','in',payment_ids.ids),('account_id','=',self.journal_id.default_debit_account_id.id)]
        move_payment_ids = self.env['account.move.line'].search(domain_move)
        return move_payment_ids

    @api.multi
    def action_review_payments(self):
        move_payment_ids = self._get_move_lines()
        #move_payment_ids.write({'statement_id': self.id})
        for move_line in move_payment_ids.filtered(lambda l: l.payment_state == 'posted'):
            name = move_line.name or move_line.ref
            ref = move_line.ref or move_line.name
            credit_line_ids = self.line_ids.filtered(lambda l: l.amount > 0 and l.date==move_line.date
                and (abs(l.amount)==move_line.payment_amount or l.name in name or l.ref in ref))
            for statement_line_id in credit_line_ids.filtered(lambda l: not l.account_id):
                if not move_line.statement_line_id:
                    move_line.write({'statement_id': self.id, 'statement_line_id': statement_line_id.id})
                    statement_line_id.write({'account_id': move_line.account_id.id,
                        'payment_method_id': move_line.payment_id.payment_method_id.id,
                        'partner_id': move_line.payment_id.partner_id.id,
                        'note': move_line.payment_id.notes,
                        'partner_name': move_line.payment_id.partner_id.display_name})

            debit_line_ids = self.line_ids.filtered(lambda l: l.amount < 0 and l.date==move_line.date
                and (abs(l.amount)==move_line.payment_amount or l.name in name or l.ref in ref))
            for statement_line_id in debit_line_ids.filtered(lambda l: not l.account_id):
                if not move_line.statement_line_id:
                    move_line.write({'statement_id': self.id, 'statement_line_id': statement_line_id.id})
                    statement_line_id.write({'account_id': move_line.account_id.id,
                        'payment_method_id': move_line.payment_id.payment_method_id.id,
                        'partner_id': move_line.payment_id.partner_id.id,
                        'note': move_line.payment_id.notes,
                        'partner_name': move_line.payment_id.partner_id.display_name})

        re_payment_ids = self.move_debit_ids + self.move_credit_ids
        remove_payment_ids = move_payment_ids.filtered(lambda m: m not in re_payment_ids)
        self.count_no_payment = len(remove_payment_ids)
        for move_line in remove_payment_ids:
            move_line.write({'statement_id': False})

    @api.multi
    def action_cancel_reconciliation(self):
        for line in self.line_ids:
            line.button_cancel_reconciliation()

    @api.multi
    def button_not_reconciled(self):
        action = self.env.ref('oe_account.action_account_payments_not_reconciled').read()[0]
        move_payment_ids = self._get_move_lines()
        re_payment_ids = self.move_debit_ids + self.move_credit_ids
        remove_payment_ids = move_payment_ids.filtered(lambda m: m not in re_payment_ids).mapped('payment_id')
        self.count_no_payment = len(remove_payment_ids)
        if len(remove_payment_ids) >= 1:
            action['domain'] = [('id', 'in', remove_payment_ids.ids)]
        return action

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method Type',
        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n"\
        "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n"\
        "Check: Pay bill by check and print it from Odoo.\n"\
        "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit,module account_batch_deposit must be installed.\n"\
        "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    transaction_type = fields.Char(string='Transaction Type')

    def button_cancel_reconciliation(self):
        aml_to_unbind =  self.env['account.move.line']
        for st_line in self:
            st_line.write({'move_name': False, 'account_id': False})
            aml_to_unbind |= st_line.journal_entry_ids
        res = super(AccountBankStatementLine, self).button_cancel_reconciliation()
        if aml_to_unbind:
            if aml_to_unbind.payment_id.state=='reconciled':
                aml_to_unbind.payment_id.write({'state': 'posted'})
            aml_to_unbind.write({'statement_id': False})
        return res


    @api.multi
    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, '%s -> %s-> %s' % (record.name, record.ref or '', record.amount)))
        return res


    @api.onchange('statement_line_id')
    def _onchage_statement_line_id(self):
        if self.statement_line_id:
            self.write({'statement_line_id': self.statement_line_id.id})

    ####################################################
    # Reconciliation methods
    ####################################################

    @api.multi
    def process_reconciliations(self, data):
        AccountMoveLine = self.env['account.move.line']
        data_copy = copy.deepcopy(data)
        for st_line, datum in pycompat.izip(self, data_copy):
            payment_aml_rec = AccountMoveLine.browse(datum.get('payment_aml_ids', []))
            payment_aml_rec.write({'statement_id': False, 'state': 'posted'})
            payment_id = payment_aml_rec.payment_id
            if payment_id:
                st_line.write({
                    'payment_method_id': payment_id.payment_method_id and payment_id.payment_method_id.id or False,
                    'partner_id': payment_id.partner_id and payment_id.partner_id.id or False,
                    'transaction_type': 'C' if st_line.amount > 0 else 'D'})
        return super(AccountBankStatementLine, self).process_reconciliations(data)

    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line
            Note: it only looks for move lines in the same currency as the statement line.
        """
        self.ensure_one()
        if not excluded_ids:
            excluded_ids = []
        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        params = {'company_id': self.env.user.company_id.id,
                    'account_payable_receivable': (self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id),
                    'amount': float_repr(float_round(amount, precision_digits=precision), precision_digits=precision),
                    'partner_id': self.partner_id.id,
                    'excluded_ids': tuple(excluded_ids),
                    'ref': self.name,
                    }
        # Look for structured communication match
        if self.name:
            add_to_select = ", CASE WHEN aml.ref = %(ref)s THEN 1 ELSE 2 END as temp_field_order "
            add_to_from = " JOIN account_move m ON m.id = aml.move_id "
            select_clause, from_clause, where_clause = self._get_common_sql_query(overlook_partner=True, excluded_ids=excluded_ids, split=True)
            sql_query = select_clause + add_to_select + from_clause + add_to_from + where_clause
            sql_query += " AND (aml.ref= %(ref)s or m.name = %(ref)s) \
                    ORDER BY temp_field_order, date_maturity desc, aml.id desc"
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

        # Look for a single move line with the same amount
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        liquidity_amt_clause = currency and '%(amount)s::numeric' or 'abs(%(amount)s::numeric)'
        select_clause, from_clause, where_clause = self._get_common_sql_query(overlook_partner=True, excluded_ids=excluded_ids, split=True)
        where_clause += " AND aml.account_id IN %(account_payable_receivable)s "
        sql_query = select_clause + add_to_select + from_clause + add_to_from + where_clause + \
                " AND ("+field+" = %(amount)s::numeric OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = " + liquidity_amt_clause + ")) \
                ORDER BY date_maturity asc, aml.id desc LIMIT 1"
        self.env.cr.execute(sql_query, params)
        results = self.env.cr.fetchone()
        if results:
            return self.env['account.move.line'].browse(results[0])

        return self.env['account.move.line']

    def get_statement_line_for_reconciliation_widget(self):
        data = super(AccountBankStatementLine, self).get_statement_line_for_reconciliation_widget()
        data['name'] = _('Description: %s Voucher: %s') % (self.name, self.ref)
        return data

    @api.multi
    def auto_reconcile(self):
        """ Try to automatically reconcile the statement.line ; return the counterpart journal entry/ies if the automatic reconciliation succeeded, False otherwise.
            TODO : this method could be greatly improved and made extensible
        """
        self.ensure_one()
        match_recs = self.env['account.move.line']

        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        params = {'company_id': self.env.user.company_id.id,
            'account_payable_receivable': (self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id),
            'amount': float_round(amount, precision_digits=precision),
            'partner_id': self.partner_id.id,
            'ref': '%s %s' % (self.name, self.ref),
        }
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        # Look for structured communication match
        if self.name:
            sql_query = self._get_common_sql_query() + \
                " AND aml.ref = %(ref)s AND ("+field+" = %(amount)s OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = %(amount)s)) \
                ORDER BY date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query, params)
            match_recs = self.env.cr.dictfetchall()
            if len(match_recs) > 1:
                return False

        # Look for a single move line with the same partner, the same amount
        if not match_recs:
            if self.partner_id:
                sql_query = self._get_common_sql_query() + \
                " AND ("+field+" = %(amount)s OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = %(amount)s)) \
                ORDER BY date_maturity asc, aml.id asc"
                self.env.cr.execute(sql_query, params)
                match_recs = self.env.cr.dictfetchall()
                if len(match_recs) > 1:
                    return False

        if not match_recs:
            return False

        match_recs = self.env['account.move.line'].browse([aml.get('id') for aml in match_recs])
        # Now reconcile
        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        for aml in match_recs:
            if aml.account_id.internal_type == 'liquidity':
                payment_aml_rec = (payment_aml_rec | aml)
            else:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                counterpart_aml_dicts.append({
                    'name': aml.name if aml.name != '/' else aml.move_id.name,
                    'debit': amount < 0 and -amount or 0,
                    'credit': amount > 0 and amount or 0,
                    'move_line': aml
                })

        try:
            with self._cr.savepoint():
                counterpart = self.process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec)
            return counterpart
        except UserError:
            # A configuration / business logic error that makes it impossible to auto-reconcile should not be raised
            # since automatic reconciliation is just an amenity and the user will get the same exception when manually
            # reconciling. Other types of exception are (hopefully) programmation errors and should cause a stacktrace.
            self.invalidate_cache()
            self.env['account.move'].invalidate_cache()
            self.env['account.move.line'].invalidate_cache()
            return False
