# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval

class AccountReportGeneralLedger(models.TransientModel):
    _inherit = 'account.report.general.ledger'

    hide_account_at_0 = fields.Boolean(string='Hide account ending balance at 0',
        help='Use this filter to hide an account or a partner with an ending balance at 0. '
             'If partners are filtered, debits and credits totals will not match the trial balance.')
    show_analytic_tags = fields.Boolean(string='Show analytic tags')
    foreign_currency = fields.Boolean(string='Show foreign currency',
        help='Display foreign currency for move lines, unless account currency is not setup through chart of accounts '
             'will display initial and final balance in that currency.', default=lambda self: self._default_foreign_currency())
    centralize = fields.Boolean(string='Activate centralization', default=True)
    receivable_accounts_only = fields.Boolean(string='Only accounts receivable')
    payable_accounts_only = fields.Boolean(string='Only accounts payable')
    account_ids = fields.Many2many(comodel_name='account.account', string='Filter accounts')
    cost_center_ids = fields.Many2many(comodel_name='account.analytic.account', string='Filter cost centers')
    partner_ids = fields.Many2many(comodel_name='res.partner', string='Filter partners', default=lambda self: self._default_partners(),)
    analytic_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', string='Filter analytical accounts')


    def _default_partners(self):
        context = self.env.context
        if context.get('active_ids') and context.get('active_model') == 'res.partner':
            partner_ids = context['active_ids']
            corp_partners = self.env['res.partner'].browse(partner_ids).filtered(lambda p: p.parent_id)
            partner_ids = set(partner_ids) - set(corp_partners.ids)
            partner_ids |= set(corp_partners.mapped('parent_id.id'))
            return list(partner_ids)


    def _default_foreign_currency(self):
        return self.env.user.has_group('base.group_multi_currency')


    def _prepare_report_general_ledger(self):
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'only_posted_moves': self.target_move == 'posted',
            'hide_account_at_0': self.hide_account_at_0,
            'foreign_currency': self.foreign_currency,
            'show_analytic_tags': self.show_analytic_tags,
            'company_id': self.company_id.id,
            'filter_account_ids': [(6, 0, self.account_ids.ids)],
            'filter_partner_ids': [(6, 0, self.partner_ids.ids)],
            'filter_cost_center_ids': [(6, 0, self.cost_center_ids.ids)],
            'filter_analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'filter_journal_ids': [(6, 0, self.journal_ids.ids)],
            'centralize': self.centralize,
            'fy_start_date': self.date_from,
        }

    def _print_report(self, data):
        if not len(self.journal_ids):
            self.journal_ids = self.env['account.journal'].search([])
        return super(AccountReportGeneralLedger, self)._print_report(data=data)
            
    @api.multi
    def button_export_html(self):
        self.ensure_one()
        action = self.env.ref('oe_account_report.action_report_general_ledger')
        action_data = action.read()[0]
        context = action_data.get('context', {})
        if isinstance(context, pycompat.string_types):
            context = safe_eval(context)
        if not len(self.journal_ids):
            self.journal_ids = self.env['account.journal'].search([])
        params = self._prepare_report_general_ledger()
        report = self.env['report_general_ledger'].create(params)
        report.compute_data_for_report()
        context.update({'active_id': report.id, 'active_ids': report.ids})
        action_data['context'] = context
        action_data['target'] = 'main'
        return action_data


    @api.multi
    def button_export_xlsx(self):
        self.ensure_one()
        if not len(self.journal_ids):
            self.journal_ids = self.env['account.journal'].search([])
        params = self._prepare_report_general_ledger()
        report = self.env['report_general_ledger'].create(params)
        report.compute_data_for_report()
        return report.print_report('xlsx')
