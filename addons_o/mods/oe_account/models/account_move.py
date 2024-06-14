# -*- coding: utf-8 -*-

import logging

from odoo import models, api, fields, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare


_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    tax_support_id = fields.Many2one('account.tax.support', string='Tax Support')
    type_document_id = fields.Many2one('account.type.document', string='Voucher type')
    authorization = fields.Char(string='Authorization', size=49)
    origin = fields.Char(string='Origin', size=50)

    @api.multi
    def assert_balanced(self):
        if not self.ids:
            return True
        prec = self.env['decimal.precision'].precision_get('Account')
        self._cr.execute("""\
            SELECT move_id, abs(sum(debit) - sum(credit)) AS amount, 
                sum(debit) AS sum_debit, sum(credit) AS sum_credit
            FROM        account_move_line
            WHERE       move_id in %s
            GROUP BY    move_id
            HAVING      abs(sum(debit) - sum(credit)) > %s
            """, (tuple(self.ids), 10 ** (-max(3, prec))))
        result = self._cr.fetchall()
        if len(result) != 0:
            for line in result:
                msg = _("Cannot create unbalanced journal entry. %s: amount %s Debit: %s Credit: %s") % (self.narration, line[1], line[2], line[3])
                _logger.critical(msg)
                #raise UserError(msg)
        return True

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    @api.depends('debit', 'credit', 'amount_currency', 'currency_id', 'matched_debit_ids', 'matched_credit_ids', 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'move_id.state')
    def _amount_residual(self):
        """ Computes the residual amount of a move line from a reconciliable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconciliable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                line.reconciled = False
                line.amount_residual = 0
                line.amount_residual_currency = 0
                continue
            #amounts in the partial reconcile table aren't signed, so we need to use abs()
            amount = abs(line.company_id.currency_id.round(line.debit) - line.company_id.currency_id.round(line.credit))
            amount_residual_currency = abs(line.amount_currency) or 0.0
            sign = 1 if (line.debit - line.credit) > 0 else -1
            if not line.debit and not line.credit and line.amount_currency and line.currency_id:
                #residual for exchange rate entries
                sign = 1 if float_compare(line.amount_currency, 0, precision_rounding=line.currency_id.rounding) == 1 else -1

            for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                # If line is a credit (sign = -1) we:
                #  - subtract matched_debit_ids (partial_line.credit_move_id == line)
                #  - add matched_credit_ids (partial_line.credit_move_id != line)
                # If line is a debit (sign = 1), do the opposite.
                sign_partial_line = sign if partial_line.credit_move_id == line else (-1 * sign)
                amount += sign_partial_line * partial_line.amount
                #getting the date of the matched item to compute the amount_residual in currency
                if line.currency_id:
                    if partial_line.currency_id and partial_line.currency_id == line.currency_id:
                        amount_residual_currency += sign_partial_line * partial_line.amount_currency
                    else:
                        if line.balance and line.amount_currency:
                            rate = line.amount_currency / line.balance
                        else:
                            date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                            rate = line.currency_id.with_context(date=date).rate
                        amount_residual_currency += sign_partial_line * line.currency_id.round(partial_line.amount * rate)

            #computing the `reconciled` field.
            reconciled = False
            digits_rounding_precision = line.company_id.currency_id.rounding
            if (line.matched_debit_ids or line.matched_credit_ids) and float_is_zero(amount, precision_rounding=digits_rounding_precision):
                if line.currency_id and line.amount_currency:
                    if float_is_zero(amount_residual_currency, precision_rounding=line.currency_id.rounding):
                        reconciled = True
                else:
                    reconciled = True
            line.reconciled = reconciled
            
            line.amount_residual = line.company_id.currency_id.round(amount * sign)
            line.amount_residual_currency = line.currency_id and line.currency_id.round(amount_residual_currency * sign) or 0.0



    debit = fields.Float(default=0.0, digits=dp.get_precision('Account'))
    credit = fields.Float(default=0.0, digits=dp.get_precision('Account'))
    amount_residual = fields.Float(compute='_amount_residual', string='Residual Amount', 
        store=True, digits=dp.get_precision('Account'),
        help="The residual amount on a journal item expressed in the company currency.")
    withholding_id = fields.Many2one('account.withholding')
    payment_amount = fields.Float(related='payment_id.amount')
    payment_state = fields.Selection(related='payment_id.state')
    tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")
    

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        # Empty self can happen if the user tries to reconcile entries which are already reconciled.
        # The calling method might have filtered out reconciled lines.
        if not self:
            return True

        #Perform all checks on lines
        company_ids = set()
        all_accounts = []
        partners = set()
        for line in self:
            company_ids.add(line.company_id.id)
            all_accounts.append(line.account_id)
            if (line.account_id.internal_type in ('receivable', 'payable')):
                partners.add(line.partner_id.id)
            if line.reconciled:
                raise UserError(_('You are trying to reconcile some entries that are already reconciled!'))
        if len(company_ids) > 1:
            raise UserError(_('To reconcile the entries company should be the same for all entries!'))
        #if len(set(all_accounts)) > 1:
        #    raise UserError(_('Entries are not of the same account!'))
        if not (all_accounts[0].reconcile or all_accounts[0].internal_type == 'liquidity'):
            raise UserError(_('The account %s (%s) is not marked as reconciliable !') % (all_accounts[0].name, all_accounts[0].code))

        #reconcile everything that can be
        remaining_moves = self.auto_reconcile_lines()

        #if writeoff_acc_id specified, then create write-off move with value the remaining amount from move in self
        if writeoff_acc_id and writeoff_journal_id and remaining_moves:
            all_aml_share_same_currency = all([x.currency_id == self[0].currency_id for x in self])
            writeoff_vals = {
                'account_id': writeoff_acc_id.id,
                'journal_id': writeoff_journal_id.id
            }
            if not all_aml_share_same_currency:
                writeoff_vals['amount_currency'] = False
            writeoff_to_reconcile = remaining_moves._create_writeoff(writeoff_vals)
            #add writeoff line to reconcile algo and finish the reconciliation
            remaining_moves = (remaining_moves + writeoff_to_reconcile).auto_reconcile_lines()
            return writeoff_to_reconcile
        return True


    @api.depends('move_id.line_ids', 'move_id.line_ids.tax_line_id', 'move_id.line_ids.debit', 'move_id.line_ids.credit')
    def _compute_tax_base_amount(self):
        for move_line in self:
            if move_line.tax_line_id:
                if move_line.withholding_id:
                    base_lines = move_line.withholding_id.withholding_line_ids.filtered(lambda line: move_line.tax_line_id in line.tax_id)
                    move_line.tax_base_amount = abs(sum(base_lines.mapped('amount_base')))
                else:
                    if move_line.tax_line_id.tax_group_id.type == 'irbpnr':
                        base_lines = move_line.invoice_id.tax_line_ids.filtered(lambda line: move_line.tax_line_id in line.tax_id)
                        move_line.tax_base_amount = abs(sum(base_lines.mapped('base')))
                    else:
                        base_lines = move_line.move_id.line_ids.filtered(lambda line: move_line.tax_line_id in line.tax_ids)
                        move_line.tax_base_amount = abs(sum(base_lines.mapped('balance')))
            else:
                move_line.tax_base_amount = 0

    @api.multi
    def _update_check(self):
        for line in self:
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.reconciled and not (line.debit == 0 and line.credit == 0):
                raise UserError(_('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s. Account %s type %s has reconciliation enabled')
                                % (err_msg, line.account_id.display_name, line.account_id.user_type_id.name))
        return super(AccountMoveLine, self)._update_check()

    @api.multi
    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        if not self:
            return True
        rec_move_ids = self.env['account.partial.reconcile']
        for account_move_line in self:
            for invoice in account_move_line.payment_id.invoice_ids:
                if invoice.id == self.env.context.get('invoice_id') and account_move_line in invoice.payment_move_line_ids:
                    account_move_line.payment_id.write({'invoice_ids': [(3, invoice.id, None)]})
            rec_move_ids += account_move_line.matched_debit_ids
            rec_move_ids += account_move_line.matched_credit_ids
        if self.env.context.get('withholding_id', False):
            current_withhold = self.env['account.withholding'].browse(self.env.context['withholding_id'])
            aml_to_keep = current_withhold.move_id.line_ids | current_withhold.move_id.line_ids.mapped('full_reconcile_id.exchange_move_id.line_ids')
            rec_move_ids = rec_move_ids.filtered(
                lambda r: (r.debit_move_id + r.credit_move_id) & aml_to_keep
            )
        elif self.env.context.get('invoice_id') and not self.env.context.get('withholding_id', False):
            current_invoice = self.env['account.invoice'].browse(self.env.context['invoice_id'])
            aml_to_keep = current_invoice.move_id.line_ids | current_invoice.move_id.line_ids.mapped('full_reconcile_id.exchange_move_id.line_ids')
            rec_move_ids = rec_move_ids.filtered(
                lambda r: (r.debit_move_id + r.credit_move_id) & aml_to_keep
            )
        return rec_move_ids.unlink()

    @api.multi
    def prepare_move_lines_for_reconciliation_widget(self, target_currency=False, target_date=False):
        res = super(AccountMoveLine, self).prepare_move_lines_for_reconciliation_widget(target_currency, target_date)
        if self._context.get('active_model') == 'account.bank.statement':
            new_res = []
            for line in res:
                new_line = line['journal_id']
                if new_line[0] == self._context.get('journal_id'):
                    new_res.append(line)
            return new_res
        return res

    @api.multi
    def write(self, vals):
        result = super(AccountMoveLine, self).write(vals)
        #when making a reconciliation on an existing liquidity journal item, mark the payment as reconciled
        for record in self:
            if record.payment_id.state == 'reconciled':
                record.payment_id.date_reconcile = record.statement_line_id.date
        return result
