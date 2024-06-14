# -*- coding: utf-8 -*-

from odoo import models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.multi
    def get_journal_dashboard_datas(self):
        currency = self.currency_id or self.company_id.currency_id
        res = super(AccountJournal, self).get_journal_dashboard_datas()
        number_authorization = number_not_authorization = not_sent_email = 0
        sum_authorization = sum_not_authorization = 0.0
        if self.type in ['sale', 'purchase']:
            (query, query_args) = self._get_invoice_authorization_query()
            self.env.cr.execute(query, query_args)
            query_results_to_authorization = self.env.cr.dictfetchall()
    
            (query, query_args) = self._get_invoice_not_authorization_query()
            self.env.cr.execute(query, query_args)
            query_results_not_authorization = self.env.cr.dictfetchall()
            
            not_sent_email = len(self.env['mail.mail'].search([]).ids)
            
            (number_authorization, sum_authorization) = self._count_results_and_sum_amounts(query_results_to_authorization, currency)
            (number_not_authorization, sum_not_authorization) = self._count_results_and_sum_amounts(query_results_not_authorization, currency)
        
        res.update({
            'number_authorization': number_authorization,
            'number_not_authorization': number_not_authorization,
            'not_sent_email': not_sent_email,
        })
        return res

    def _get_invoice_authorization_query(self):
        """
        Returns a tuple contaning the SQL query used to gather the open bills
        data as its first element, and the arguments dictionary to use to run
        it as its second.
        """
        return ("""SELECT state, amount_total, currency_id AS currency, type
                  FROM account_invoice
                  WHERE journal_id = %(journal_id)s AND is_electronic = True
                  AND "authorization" = True AND state IN ('open','paid');""", {'journal_id':self.id})

    def _get_invoice_not_authorization_query(self):
        """
        Returns a tuple contaning the SQL query used to gather the open bills
        data as its first element, and the arguments dictionary to use to run
        it as its second.
        """
        return ("""SELECT state, amount_total, currency_id AS currency, type
                  FROM account_invoice
                  WHERE journal_id = %(journal_id)s AND is_electronic = True
                  AND "authorization" = False AND state NOT IN ('cancel');""", {'journal_id':self.id})

    @api.multi
    def action_authorization(self):
        """return action based on type for related journals"""
        action_name = self._context.get('action_name', False)
        if not action_name:
            if self.type == 'bank':
                action_name = 'action_bank_statement_tree'
            elif self.type == 'cash':
                action_name = 'action_view_bank_statement_tree'
            elif self.type == 'sale':
                action_name = 'action_invoice_tree1'
            elif self.type == 'purchase':
                action_name = 'action_invoice_tree2'
            else:
                action_name = 'action_move_journal_line'

        _journal_invoice_type_map = {
            ('sale', None): 'out_invoice',
            ('purchase', None): 'in_invoice',
            ('sale', 'refund'): 'out_refund',
            ('purchase', 'refund'): 'in_refund',
            ('bank', None): 'bank',
            ('cash', None): 'cash',
            ('general', None): 'general',
        }
        invoice_type = _journal_invoice_type_map[(self.type, self._context.get('invoice_type'))]

        ctx = self._context.copy()
        ctx.pop('group_by', None)
        ctx.update({
            'journal_type': self.type,
            'default_journal_id': self.id,
            'default_type': invoice_type,
            'type': invoice_type
        })

        [action] = self.env.ref('account.%s' % action_name).read()
        if not self.env.context.get('use_domain'):
            ctx['search_default_journal_id'] = self.id
        action['context'] = ctx
        action['domain'] = self._context.get('use_domain', [])
        account_invoice_filter = self.env.ref('account.view_account_invoice_filter', False)
        if action_name in ['action_invoice_tree1', 'action_invoice_tree2']:
            action['search_view_id'] = account_invoice_filter and account_invoice_filter.id or False
        if action_name in ['action_bank_statement_tree', 'action_view_bank_statement_tree']:
            action['views'] = False
            action['view_id'] = False
        return action

    @api.multi
    def action_open_email(self):
        action = self.env.ref('mail.action_view_mail_mail').read()[0]
        return action

