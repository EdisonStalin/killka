# -*- coding: utf-8 -*-

import logging
from ast import literal_eval

from odoo import models, fields, api


_logger = logging.getLogger(__name__)

class Partner(models.Model):
    _inherit = 'res.partner'
    
    def _invoice_total(self):
        super(Partner, self)._invoice_total()
        for partner in self: 
            partner.count_authorization = self.env['account.authorization'].search_count([('partner_id','=',partner.id)])
        

    count_authorization = fields.Integer(compute='_invoice_total', string="Count Authorization",
        groups='account.group_account_invoice')
    type_supplier = fields.Selection([('01', 'Natural Person'), ('02', 'Society')], 'Type Supplier', default='01', help="Type of Supplier Identification")
    check_accounting = fields.Boolean('Check Acconting', default=True, copy=False, help='Natural or legal person obliged to keep accounts')
    limit_amount = fields.Float(default=0.0, help='Limit of the amount the customer can invoice')
    method_id = fields.Many2one('account.method.payment', string='Payment Method', help='Choose the form of payment made by the client')
    account_expense_id = fields.Many2one('account.account', string="Account Expense", domain="[('internal_type', 'not in', ['payable', 'receivable']), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner")
    account_income_id = fields.Many2one('account.account', string="Account Income", domain="[('internal_type', 'not in', ['payable', 'receivable']), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner")


    @api.model
    def default_get(self, default_fields):
        res = super(Partner, self).default_get(default_fields)
        company_id = self.env.user.company_id
        if not res.get('property_account_payable_id', False):
            res['property_account_payable_id'] = company_id.property_account_payable_id.id or False
        if not res.get('property_account_receivable_id', False):
            res['property_account_receivable_id'] = company_id.property_account_receivable_id.id or False
        if 'method_id' not in res:
            res['method_id'] = self.env.ref('oe_account.payment_method_20').id
        return res


    @api.model
    def create(self, vals):
        if 'method_id' not in vals:
            vals['method_id'] = self.env.ref('oe_account.payment_method_20').id
        return super(Partner, self).create(vals)


    @api.onchange('company_type')
    def _onchange_company_type(self):
        if self.company_type == 'person':
            self.type_supplier = '01'
        else:
            self.type_supplier = '02'


    @api.multi
    def _get_info_partner(self, value, customer=False):
        company = self.env.user.company_id
        domain = [('vat', '=', value['vat']), ('is_validation_vat', '=', True), ('company_id', '=', company.id)]
        partner_id = self.env['res.partner'].with_context(active_test=False).search(domain, limit=1, order='id asc')
        if not partner_id:
            value.update({
                'company_id': company.id,
                'is_validation_vat': True,
                'customer': customer,
                'supplier': True if not customer else False,
                'type': 'contact',
                'company_type': 'person',
                'type_supplier': '01',
                'property_account_receivable_id': company.property_account_receivable_id.id or False,
                'property_account_payable_id': company.property_account_payable_id.id or False,
                'property_supplier_payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
                'property_payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
                'method_id': self.env.ref('oe_account.payment_method_20').id,
            })
            try:
                partner_id = partner_id.create(value)
            except BaseException as e:
                _logger.info(e.name)
        if not partner_id.property_account_receivable_id:
            partner_id.property_account_receivable_id = company.property_account_receivable_id.id
        if not partner_id.property_account_payable_id:
            partner_id.property_account_payable_id = company.property_account_payable_id.id
        return partner_id

    @api.multi
    def action_view_partner_authorizations(self):
        self.ensure_one()
        action = self.env.ref('oe_account.action_authorization_external_form').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.id))
        return action

