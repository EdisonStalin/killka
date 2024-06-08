#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat

class AccountPrintJournal(models.TransientModel):
    _inherit = "account.print.journal"


    group_option = fields.Selection(selection='_get_group_options', string="Group entries by", default='journal', required=True)
    foreign_currency = fields.Boolean()
    with_account_name = fields.Boolean(default=False)


    @api.model
    def _get_move_targets(self):
        return [
            ('all', _("All")),
            ('posted', _("Posted")),
            ('draft', _("Not Posted"))
        ]

    @api.model
    def _get_sort_options(self):
        return [
            ('move_name', _("Entry number")),
            ('date', _("Date")),
        ]

    @api.model
    def _get_group_options(self):
        return [
            ('journal', _("Journal")),
            ('none', _("No group")),
        ]

    @api.multi
    def button_export_html(self):
        self.ensure_one()
        action = self.env.ref('oe_account_report.action_report_journal_ledger')
        vals = action.read()[0]
        context1 = vals.get('context', {})
        if isinstance(context1, pycompat.string_types):
            context1 = safe_eval(context1)
        params = self._prepare_report_journal_ledger()
        report = self.env['report_journal_ledger'].create(params)
        report.compute_data_for_report()
        context1.update({'active_id': report.id, 'active_ids': report.ids})
        vals['context'] = context1
        vals['target'] = 'main'
        return vals


    @api.multi
    def button_export_xlsx(self):
        self.ensure_one()
        params = self._prepare_report_journal_ledger()
        report = self.env['report_journal_ledger'].create(params)
        report.compute_data_for_report()
        return report.print_report('xlsx')
        

    def _prepare_report_journal_ledger(self):
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'move_target': self.target_move,
            'foreign_currency': self.foreign_currency,
            'company_id': self.company_id.id,
            'journal_ids': [(6, 0, self.journal_ids.ids)],
            'sort_option': self.sort_selection,
            'group_option': self.group_option,
            'with_account_name': self.with_account_name,
        }
