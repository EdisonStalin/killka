#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountComplementaryReport(models.TransientModel):
    _inherit = "account.common.report"
    _name = 'account.complementary.report'
    _description = 'Complementary Report'
    
    report_options = fields.Selection([('account_state', 'Account State'),], string='Report', 
                                     default='account_state', required=True)
    type_partner = fields.Selection([('customer', 'Customer'),
                                     ('supplier', 'Supplier')], string='Type Partner', 
                                     default='customer', required=True)
    partner_ids = fields.Many2many('res.partner', string='Partners')
    
    
    @api.onchange('type_partner')
    def onchange_type_partner(self):
        self.partner_ids = []
        res = {}
        domain = [('company_id', '=', self.company_id.id)]
        if self.type_partner == 'customer': domain += [('customer', '=', True)]
        if self.type_partner == 'supplier': domain += [('supplier', '=', True)]
        if self.type_partner == 'both': domain += [('customer', '=', True), ('supplier', '=', True)]
        partner_ids = self.env['res.partner'].search(domain)
        res['domain'] = {'partner_ids': [('id', 'in', partner_ids.ids)]}
        return res


    def _print_report(self, data):
        data['form'].update(self.read(['report_options', 'type_partner', 'partner_ids'])[0])
        return self.env.ref('oe_account_report.action_report_account_complementary').with_context(landscape=True).report_action(self, data=data)


