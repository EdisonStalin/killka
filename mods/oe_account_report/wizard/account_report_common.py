# -*- coding: utf-8 -*-

import time

from odoo import models, api, fields

class AccountCommonReport(models.TransientModel):
    _inherit = "account.common.report"

    def _init_date_from(self):
        """set start date to begin of current year if fiscal year running"""
        today = fields.Date.context_today(self)
        cur_month = fields.Date.from_string(today).month
        cur_day = fields.Date.from_string(today).day
        last_fsc_month = self.env.user.company_id.fiscalyear_last_month
        last_fsc_day = self.env.user.company_id.fiscalyear_last_day
        if cur_month < last_fsc_month \
                or cur_month == last_fsc_month and cur_day <= last_fsc_day:
            return time.strftime('%Y-01-01')

    date_from = fields.Date(required=True, default=lambda self: self._init_date_from())
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Filter Analytical Accounts')


    def _build_contexts(self, data):
        result = super(AccountCommonReport, self)._build_contexts(data)
        result['analytic_account_ids'] = 'analytic_account_ids' in data['form'] and data['form']['analytic_account_ids'] or False
        return result


    @api.multi
    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'analytic_account_ids'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self.with_context(discard_logo_check=True)._print_report(data)
    
