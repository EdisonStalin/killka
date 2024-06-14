# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    

    @api.multi
    def get_journal_dashboard_datas(self):
        currency = self.currency_id or self.company_id.currency_id
        res = super(AccountJournal, self).get_journal_dashboard_datas()
        number_paid = number_cancel = 0
        sum_paid = sum_cancel = 0.0
        if self.type in ['sale', 'purchase']:
            (query, query_args) = self._get_paid_bills_query()
            self.env.cr.execute(query, query_args)
            query_results_paid = self.env.cr.dictfetchall()
            
            (query, query_args) = self._get_cancel_bills_query()
            self.env.cr.execute(query, query_args)
            query_results_cancel = self.env.cr.dictfetchall()
            
            (number_paid, sum_paid) = self._count_results_and_sum_amounts(query_results_paid, currency)
            (number_cancel, sum_cancel) = self._count_results_and_sum_amounts(query_results_cancel, currency)
        
        res.update({
            'number_paid': number_paid,
            'sum_paid': formatLang(self.env, currency.round(sum_paid) + 0.0, currency_obj=currency),
            'number_cancel': number_cancel,
            'sum_cancel': formatLang(self.env, currency.round(sum_cancel) + 0.0, currency_obj=currency),
        })
        return res


    def _get_paid_bills_query(self):
        """
        Returns a tuple contaning the SQL query used to gather the open bills
        data as its first element, and the arguments dictionary to use to run
        it as its second.
        """
        return ("""SELECT state, amount_total, currency_id AS currency, type
                  FROM account_invoice
                  WHERE journal_id = %(journal_id)s AND state = 'paid';""", {'journal_id':self.id})
        
    def _get_cancel_bills_query(self):
        """
        Returns a tuple contaning the SQL query used to gather the open bills
        data as its first element, and the arguments dictionary to use to run
        it as its second.
        """
        return ("""SELECT state, amount_total, currency_id AS currency, type
                  FROM account_invoice
                  WHERE journal_id = %(journal_id)s AND state = 'cancel';""", {'journal_id':self.id})

    @api.multi
    def action_create_new(self):
        res = super(AccountJournal, self).action_create_new()
        ctx = self._context.copy()
        ctx.update({'default_journal_id': self.id})
        if self.establishment_id:
            ctx.update({'default_establishment_id': self.establishment_id.id})
        if self.authorization_id:
            ctx.update({
                'default_authorization_id': self.authorization_id.id,
                'default_type_document_id': self.authorization_id.type_document_id.id,
                'default_is_electronic': self.authorization_id.is_electronic,
            })
        res['context'] = ctx
        return res

    """@api.multi
    def action_open_reconcile(self):
        if self.type in ['bank', 'cash']:
            # Open reconciliation view for bank statements belonging to this journal
            action_name = 'account.action_bank_statement_tree'
            action = self.env.ref(action_name).read()[0]
            bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)])
            action['context'] = {'statement_ids': bank_stmt.ids, 'company_ids': self.mapped('company_id').ids}
            action['domain'] = [('journal_id', 'in', self.ids)]
            return action
        return super(AccountJournal, self).action_open_reconcile()"""


