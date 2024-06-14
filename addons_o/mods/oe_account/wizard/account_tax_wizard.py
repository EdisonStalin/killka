# -*- coding: utf-8 -*-

import base64

from odoo import models, fields, api, _
from odoo.tools.mimetypes import guess_mimetype
from odoo.exceptions import UserError

PARAMS = {
    'start': ('account.account')
}

options = {'headers': True, 'advanced': True, 'keep_matches': False, 
           'encoding': 'utf-8', 'separator': ',', 'quoting': '"', 
           'date_format': '', 'datetime_format': '', 'float_thousand_separator': ',',
           'float_decimal_separator': '.', 'fields': []}

class AccountTaxWizard(models.TransientModel):
    _name = "account.tax.wizard"
    _inherit = ['multi.step.wizard.mixin']
    _description = "Account Tax Step Wizard"

    @api.model
    def _default_chart_template_id(self):
        company_id = self.env.user.company_id
        return company_id.chart_template_id

    type = fields.Selection(selection=[('import','Import'),('template', 'Template')], string='Action', default='template')
    files = fields.Binary(string="Import File")
    datas_fname = fields.Char('Import File Name')
    name = fields.Char(string='Chart of Accounts', required=True) 
    chart_template_id = fields.Many2one('account.chart.template', string='Current Chart of Accounts',
        default=_default_chart_template_id, help='The chart template for the company (if any)')
    account_ids = fields.Many2many('account.account', 'accounts_rel',
        'account_id', 'wacc_id', string='Accounts')
    tax_ids = fields.Many2many('account.tax', 'taxes_rel',
        'tax_id', 'wtax_id', string='Available Taxes')
    template_taxes_ids = fields.Many2many('account.tax.template', 'template_tax_rel',
        'template_tax_id', 'wtax_id', string='Enable Taxes')


    @api.model
    def _selection_state(self):
        return [
            ('start', _('Templates for Account Chart')),
            ('chart', _('Templates for Account Chart')),
            ('enable', _('Tax Available')),
            ('taxes', _('Tax Setup Wizard')),
            ('final', _('Finish')),
        ]

    def _check_chart_account(self, company_id):
        name = _('Chart of Accounts - %s') % company_id.name
        chart_template_id = company_id.chart_template_id
        if chart_template_id:
            name = chart_template_id.name
        return chart_template_id, name

    @api.model
    def default_get(self, default_fields):
        res = super(AccountTaxWizard, self).default_get(default_fields)
        company_id = self.env.user.company_id
        if 'chart_template_id' not in res or not res.get('chart_template_id'):
            chart_template_id, name = self._check_chart_account(company_id)
            res['name'] = name
            res['chart_template_id'] = chart_template_id and chart_template_id.id or False
        return res
    
    def open_next(self):
        res = super(AccountTaxWizard, self).open_next()
        return res
    
    def state_exit_start(self):
        account_ids = self.env['account.account'].search([('deprecated','=',False)])
        for account in account_ids:
            account.write({'code': '%s-Deprecated' % account.code, 'deprecated': True})
        account_ids._cr.commit()
        file_type = guess_mimetype(self.files)
        vals = {
            'res_model': 'account.account',
            'file': base64.b64decode(self.files),
            'file_name': self.name,
            'file_type': file_type,
        }
        file_import = self.env['base_import.import'].create(vals)
        result = file_import.parse_preview(options, count=100)
        import_result = file_import.do(result.get('headers', []), result.get('options', {}), dryrun=True)
        messages  = alert = []
        if len(import_result):
            for line in import_result:
                if line['type'] == 'error':
                    messages.append(_('Row: %s Type: %s Message: %s') % (line.get('record', 0), line['type'], line['message']))
                else:
                    alert.append(_('Row: %s Type: %s Message: %s') % (line.get('record', 0), line['type'], line['message']))
        if len(messages):
            raise UserError('.\n'.join(messages))
        else:
            self.state = 'chart'


    def state_exit_chart(self):
        self.state = 'enable'

    def state_exit_enable(self):
        self.state = 'final'

    def state_exit_final(self):
        self.state = 'final'

    @api.multi
    def action_disable_taxes(self):
        taxes_ids = self.env['account.tax'].search([])
        for tax_id in taxes_ids:
            line_ids = self.env['account.move.line'].search([('tax_line_id','=',tax_id.id)])
            qty = len(line_ids)
            tax_id.write({
                'sequence': qty,
                'active': True if qty > 0 else False,
            })
        taxes_ids = self.env['account.tax'].search([('active','=',True)])
        for tax_id in taxes_ids:
            xml_id = self.env['ir.model.data'].search([('res_id','=',tax_id.id), ('module','=','oe_template_super'), ('model','=','account.account')])
            domain = [('name','=',tax_id.name),('type_tax_use','=',tax_id.type_tax_use),('form_code_ats','=',tax_id.form_code_ats)]
            if xml_id: domain += [('id','=',xml_id.res_id)]       
            tmp_tax_id = self.env['account.tax.template'].search(domain)
            if xml_id.res_id == tax_id.id:
                tax_id.write({
                    'form_code_ats': tmp_tax_id.form_code_ats,
                    'code_form_id': tmp_tax_id.code_form_id and tmp_tax_id.code_form_id.id or False,
                    'refund_code_form_id': tmp_tax_id.refund_code_form_id and tmp_tax_id.refund_code_form_id.id or False,
                    'code_applied_id': tmp_tax_id.code_applied_id and tmp_tax_id.code_applied_id.id or False,
                    'tag_ids': [(6, 0 ,tmp_tax_id.tag_ids.ids)],
                })
        self.tax_ids = taxes_ids
        return self._reopen_self()
        
    