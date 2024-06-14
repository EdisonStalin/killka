# -*- coding: utf-8 -*-

import time

from odoo import models, api, _
from odoo.exceptions import UserError

class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"


    @api.multi
    def button_confirm_bank(self):
        self._balance_check()
        statements = self.filtered(lambda r: r.state == 'open')
        for statement in statements:
            moves = self.env['account.move']
            # `line.journal_entry_ids` gets invalidated from the cache during the loop
            # because new move lines are being created at each iteration.
            # The below dict is to prevent the ORM to permanently refetch `line.journal_entry_ids`
            line_journal_entries = {line: line.journal_entry_ids for line in statement.line_ids}
            for st_line in statement.line_ids:
                self._concile_invoice_refund(st_line)
                journal_entries = line_journal_entries[st_line]
                if st_line.account_id and not journal_entries.ids:
                    payment_methods = (st_line.amount>0) and st_line.journal_id.inbound_payment_method_ids or st_line.journal_id.outbound_payment_method_ids
                    if not payment_methods:
                        raise UserError(_('The payment method %s, enable payment methods or pay, for amount %s') % (st_line.journal_id.name, st_line.amount))
                    st_line.fast_counterpart_creation()
                elif not journal_entries.ids and not statement.currency_id.is_zero(st_line.amount):
                    msg = _("""All the account entries lines must be processed in order to close the statement. 
                        Problem in %s of %s: amount %s""" % (st_line.name, st_line.pos_statement_id.pos_reference, st_line.amount))
                    raise UserError(msg)

            moves = statement.mapped('line_ids.journal_entry_ids.move_id')
            if moves:
                moves.filtered(lambda m: m.state != 'posted').post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
        statements.link_bank_to_partner()
        statements.write({'state': 'confirm', 'date_done': time.strftime("%Y-%m-%d %H:%M:%S")})
        
        
    def _concile_invoice_refund(self, line, apply_return=False):
        invoice_first = self.env['account.invoice']
        order = line.pos_statement_id or False
        if order:
            refund = self.env['account.invoice'].search([('create_order_id', '=', order.id), ('type', '=', 'out_refund'), ('state', '=', 'open')])
            if refund:
                # if apply return invoice the origin
                order_id = refund.create_order_id
                if order_id.session_id.state == 'closing_control':
                    invoice_first += order_id.invoice_id
                else:
                    invoice_first += order.invoice_id
            if invoice_first and refund:
                credit_aml_id = refund.move_id.line_ids.filtered(lambda l: l.account_id.id==invoice_first.account_id.id \
                                                                     and l.reconciled==False and l.credit>0 and l.debit==0 \
                                                                     and l.amount_residual != 0.0)
                invoice_first.assign_outstanding_credit(credit_aml_id.id)

