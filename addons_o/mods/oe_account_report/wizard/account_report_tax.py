# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat


class AccountTaxReport(models.TransientModel):
    _inherit = 'account.tax.report'
    
    based_on = fields.Selection([('taxtags', 'Tax Tags'), ('taxgroups', 'Tax Groups')], string='Based On', required=True, default='taxtags')
    tax_detail = fields.Boolean(string='Detail Taxes')
    

    @api.multi
    def button_export_html(self):
        self.ensure_one()
        action = self.env.ref('oe_account_report.action_report_vat_report')
        vals = action.read()[0]
        context1 = vals.get('context', {})
        if isinstance(context1, pycompat.string_types):
            context1 = safe_eval(context1)
        params = self._prepare_vat_report()
        report = self.env['report_vat_report'].create(params)
        report.compute_data_for_report()
        context1.update({'active_id': report.id, 'active_ids': report.ids})
        vals['context'] = context1
        vals['target'] = 'main'
        return vals


    @api.multi
    def button_export_xlsx(self):
        self.ensure_one()
        params = self._prepare_vat_report()
        report = self.env['report_vat_report'].create(params)
        report.compute_data_for_report()
        return report.print_report('xlsx')


    def _prepare_vat_report(self):
        return {
            'company_id': self.company_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'based_on': self.based_on,
            'tax_detail': self.tax_detail,
        }
