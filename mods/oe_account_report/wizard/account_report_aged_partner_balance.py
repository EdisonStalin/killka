#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval

class AccountAgedTrialBalance(models.TransientModel):

    _inherit = 'account.aged.trial.balance'

    partner_ids = fields.Many2many(comodel_name='res.partner', string='Filter partners',)
    show_move_line_details = fields.Boolean(string='Show move line details')
    receivable_accounts_only = fields.Boolean(string='Only accounts receivable')
    payable_accounts_only = fields.Boolean(string='Only accounts payable')
    account_ids = fields.Many2many(comodel_name='account.account', string='Filter accounts')


    @api.onchange('receivable_accounts_only', 'payable_accounts_only')
    def _onchange_type_accounts_only(self):
        """Handle receivable/payable accounts only change."""
        if self.receivable_accounts_only or self.payable_accounts_only:
            domain = [('company_id', '=', self.company_id.id)]
            if self.receivable_accounts_only and self.payable_accounts_only:
                domain += [('internal_type', 'in', ('receivable', 'payable'))]
            elif self.receivable_accounts_only:
                domain += [('internal_type', '=', 'receivable')]
            elif self.payable_accounts_only:
                domain += [('internal_type', '=', 'payable')]
            self.account_ids = self.env['account.account'].search(domain)
        else:
            self.account_ids = None


    @api.multi
    def button_export_html(self):
        self.ensure_one()
        action = self.env.ref('oe_account_report.action_report_aged_partner_balance')
        vals = action.read()[0]
        context1 = vals.get('context', {})
        if isinstance(context1, pycompat.string_types):
            context1 = safe_eval(context1)
        params = self._prepare_report_aged_partner_balance()
        report = self.env['report_aged_partner_balance'].create(params)
        report.compute_data_for_report()
        context1.update({'active_id': report.id, 'active_ids': report.ids})
        vals['context'] = context1
        vals['target'] = 'main'
        return vals


    @api.multi
    def button_export_xlsx(self):
        self.ensure_one()
        params = self._prepare_report_aged_partner_balance()
        report = self.env['report_aged_partner_balance'].create(params)
        report.compute_data_for_report()
        return report.print_report('xlsx')


    def _prepare_report_aged_partner_balance(self):
        return {
            'date_at': self.date_from,
            'only_posted_moves': self.target_move == 'posted',
            'company_id': self.company_id.id,
            'filter_account_ids': [(6, 0, self.account_ids.ids)],
            'filter_partner_ids': [(6, 0, self.partner_ids.ids)],
            'show_move_line_details': self.show_move_line_details,
        }
    