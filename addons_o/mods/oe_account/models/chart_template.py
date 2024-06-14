# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    property_receivable_journal_id = fields.Many2one('account.journal', string="Default Sale Journal")
    property_payable_journal_id = fields.Many2one('account.journal', string="Default Purchase Journal")
    transfer_account_id = fields.Many2one('account.account.template', required=False, string='Transfer Account',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id)],
        help="Intermediary account used when moving money from a liquidity account to another")

    def _get_tax_template(self, parent_id):
        result = []
        domain = [('chart_template_id','=',parent_id),'|',('active','=', False),('active','=',True)]
        tax_template_ids = self.env['account.tax.template'].with_context(active_test=True).search(domain)
        for line in tax_template_ids:
            values = {}
            for name, field in line._fields.items():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'tag_ids':
                    values[name] = [(6, 0, line[name].ids)]
            result.append((0, 0, values))
        return result

    @api.model
    def create(self, vals):
        chart_id = False
        if 'parent_id' in vals:
            chart_id = self.env['account.chart.template'].browse(vals['parent_id'])
            tax_template_ids = self._get_tax_template(vals['parent_id'])
            vals['tax_template_ids'] = tax_template_ids
        if not vals['transfer_account_id'] and chart_id:
            vals['transfer_account_id'] = chart_id.transfer_account_id and chart_id.transfer_account_id.id
        res = super(AccountChartTemplate, self).create(vals)
        return res

    @api.model
    def default_get(self, default_fields):
        company_id = self.env.user.company_id
        res = super(AccountChartTemplate, self).default_get(default_fields)
        if 'currency_id' not in res:
            res['currency_id'] = company_id.currency_id.id
        return res

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        """
        This method is used for creating journals.

        :param chart_temp_id: Chart Template Id.
        :param acc_template_ref: Account templates reference.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        JournalObj = self.env['account.journal']
        for vals_journal in self._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict):
            journal = JournalObj.create(vals_journal)
            if vals_journal['type'] == 'sale' and vals_journal['code'] == _('VEN'):
                company.write({'property_receivable_journal_id': journal.id})
            if vals_journal['type'] == 'purchase' and vals_journal['code'] == _('COMP'):
                company.write({'property_payable_journal_id': journal.id})

        return True


    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journals = [{'name': 'Ventas', 'type': 'sale', 'code': _('VEN'),
                     'favorite': True, 'color': 11, 'sequence': 5, 'show_on_dashboard': True, 'update_posted': True},
                    {'name': 'Compras', 'type': 'purchase', 'code': _('COMP'),
                     'favorite': True, 'color': 11, 'sequence': 6, 'show_on_dashboard': True, 'update_posted': True},]
        if journals_dict != None:
            journals.extend(journals_dict)

        self.ensure_one()
        journal_data = []
        for journal in journals:
            vals = {
                'type': journal['type'],
                'name': journal['name'],
                'code': journal['code'],
                'company_id': company.id,
                'show_on_dashboard': journal['favorite'],
                'color': journal.get('color', False),
                'sequence': journal['sequence'],
                'show_on_dashboard': journal['show_on_dashboard'],
                'update_posted': journal['update_posted']
            }
            journal_data.append(vals)
        return journal_data


    @api.multi
    def generate_properties(self, acc_template_ref, company):
        """
        This method used for creating properties.

        :param self: chart templates for which we need to create properties
        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        self.ensure_one()
        PropertyObj = self.env['ir.property']
        todo_list = [
            ('property_account_receivable_id', 'res.partner', 'account.account'),
            ('property_account_payable_id', 'res.partner', 'account.account'),
            ('property_account_expense_categ_id', 'product.category', 'account.account'),
            ('property_account_income_categ_id', 'product.category', 'account.account'),
            ('property_account_expense_id', 'product.template', 'account.account'),
            ('property_account_income_id', 'product.template', 'account.account'),
        ]
        for record in todo_list:
            account = getattr(self, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = self.env['ir.model.fields'].search([('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])], limit=1)
                vals = {
                    'name': record[0],
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': value,
                }
                properties = PropertyObj.search([('name', '=', record[0]), ('company_id', '=', company.id)])
                if properties:
                    #the property exist: modify it
                    properties.write(vals)
                else:
                    #create the property
                    PropertyObj.create(vals)
        stock_properties = [
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
            'property_account_receivable_id',
            'property_account_payable_id',
            'property_account_expense_id',
            'property_account_income_id',
        ]
        for stock_property in stock_properties:
            account = getattr(self, stock_property)
            value = account and acc_template_ref[account.id] or False
            if value:
                company.write({stock_property: value})
        return True


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    type_tax_use = fields.Selection(selection_add=[('all', 'All')])
    form_code_ats = fields.Char('Form code anexo', size=4, help='Unique code anexo (ATS) related to the tax')
    code_form_id = fields.Many2one('account.account.tag', string='Tax Settlement')
    refund_code_form_id = fields.Many2one('account.account.tag', string='Tax Settlement')
    code_applied_id = fields.Many2one('account.account.tag', string='Tax Settlement Applied')
    invoice_repartition_line_ids = fields.One2many(string="Repartition for Invoices", comodel_name="account.tax.repartition.line.template", inverse_name="invoice_tax_id", copy=True, help="Repartition when the tax is used on an invoice")
    refund_repartition_line_ids = fields.One2many(string="Repartition for Refund Invoices", comodel_name="account.tax.repartition.line.template", inverse_name="refund_tax_id", copy=True, help="Repartition when the tax is used on a refund")
    module = fields.Selection([('pay_res', _('Payments to residents')), 
                               ('pay_no_res', _('payments to non-residents'))], 'Module', help="Concepts of retention in the source of income tax (AIR)")


    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('ALTER TABLE "account_tax_template" DROP CONSTRAINT IF EXISTS "account_tax_template_name_company_uniq"')


    @api.multi
    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        val['form_code_ats'] = self.form_code_ats
        val['code_form_id'] = self.code_form_id and self.code_form_id.id or False
        val['module'] = self.module
        
        # We add repartition lines if there are some, so that if there are none,
        # default_get is called and creates the default ones properly.
        if self.invoice_repartition_line_ids:
            val['invoice_repartition_line_ids'] = self.invoice_repartition_line_ids.get_repartition_line_create_vals(company)
        if self.refund_repartition_line_ids:
            val['refund_repartition_line_ids'] = self.refund_repartition_line_ids.get_repartition_line_create_vals(company)

        return val


class AccountTaxRepartitionLineTemplate(models.Model):
    _name = "account.tax.repartition.line.template"
    _description = "Tax Repartition Line Template"

    factor_percent = fields.Float(string="%", required=True, help="Factor to apply on the account move lines generated from this distribution line, in percents")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    account_id = fields.Many2one(string="Account", comodel_name='account.account.template', help="Account on which to post the tax amount")
    invoice_tax_id = fields.Many2one(comodel_name='account.tax.template', help="The tax set to apply this distribution on invoices. Mutually exclusive with refund_tax_id")
    refund_tax_id = fields.Many2one(comodel_name='account.tax.template', help="The tax set to apply this distribution on refund invoices. Mutually exclusive with invoice_tax_id")
    tag_ids = fields.Many2many(string="Financial Tags", relation='account_tax_repartition_financial_tags', comodel_name='account.account.tag', copy=True, help="Additional tags that will be assigned by this repartition line for use in financial reports")
    use_in_tax_closing = fields.Boolean(string="Tax Closing Entry")

    # These last two fields are helpers used to ease the declaration of account.account.tag objects in XML.
    # They are directly linked to account.tax.report.line objects, which create corresponding + and - tags
    # at creation. This way, we avoid declaring + and - separately every time.
    plus_report_line_ids = fields.Many2many(string="Plus Tax Report Lines", relation='account_tax_repartition_plus_report_line', comodel_name='account.tax.report.line', copy=True, help="Tax report lines whose '+' tag will be assigned to move lines by this repartition line")
    minus_report_line_ids = fields.Many2many(string="Minus Report Lines", relation='account_tax_repartition_minus_report_line', comodel_name='account.tax.report.line', copy=True, help="Tax report lines whose '-' tag will be assigned to move lines by this repartition line")

    @api.model
    def create(self, vals):
        if vals.get('plus_report_line_ids'):
            vals['plus_report_line_ids'] = self._convert_tag_syntax_to_orm(vals['plus_report_line_ids'])

        if vals.get('minus_report_line_ids'):
            vals['minus_report_line_ids'] = self._convert_tag_syntax_to_orm(vals['minus_report_line_ids'])

        if vals.get('tag_ids'):
            vals['tag_ids'] = self._convert_tag_syntax_to_orm(vals['tag_ids'])

        if vals.get('use_in_tax_closing') is None:
            if not vals.get('account_id'):
                vals['use_in_tax_closing'] = False
            else:
                internal_type = self.env['account.account.template'].browse(vals.get('account_id')).user_type_id.type
                vals['use_in_tax_closing'] = not (internal_type == 'income' or internal_type == 'expense')

        return super(AccountTaxRepartitionLineTemplate, self).create(vals)

    @api.model
    def _convert_tag_syntax_to_orm(self, tags_list):
        """ Repartition lines give the possibility to directly give
        a list of ids to create for tags instead of a list of ORM commands.

        This function checks that tags_list uses this syntactic sugar and returns
        an ORM-compliant version of it if it does.
        """
        if tags_list and all(isinstance(elem, int) for elem in tags_list):
            return [(6, False, tags_list)]
        return tags_list

    @api.constrains('invoice_tax_id', 'refund_tax_id')
    def validate_tax_template_link(self):
        for record in self:
            if record.invoice_tax_id and record.refund_tax_id:
                raise ValidationError(_("Tax distribution line templates should apply to either invoices or refunds, not both at the same time. invoice_tax_id and refund_tax_id should not be set together."))

    @api.constrains('plus_report_line_ids', 'minus_report_line_ids')
    def validate_tags(self):
        all_tax_rep_lines = self.mapped('plus_report_line_ids') + self.mapped('minus_report_line_ids')
        lines_without_tag = all_tax_rep_lines.filtered(lambda x: not x.tag_name)
        if lines_without_tag:
            raise ValidationError(_("The following tax report lines are used in some tax distribution template though they don't generate any tag: %s . This probably means you forgot to set a tag_name on these lines.", str(lines_without_tag.mapped('name'))))

    def get_repartition_line_create_vals(self, company):
        rslt = [(5, 0, 0)]
        for record in self:
            tags_to_add = self.env['account.account.tag']
            tags_to_add += record.plus_report_line_ids.mapped('tag_ids').filtered(lambda x: not x.tax_negate)
            tags_to_add += record.minus_report_line_ids.mapped('tag_ids').filtered(lambda x: x.tax_negate)
            tags_to_add += record.tag_ids

            rslt.append((0, 0, {
                'factor_percent': record.factor_percent,
                'repartition_type': record.repartition_type,
                'tag_ids': [(6, 0, tags_to_add.ids)],
                'company_id': company.id,
                'use_in_tax_closing': record.use_in_tax_closing
            }))
        return rslt


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'


    property_receivable_journal_id = fields.Many2one('account.journal', string="Default Sale Journal")
    property_payable_journal_id = fields.Many2one('account.journal', string="Default Purchase Journal")
    property_account_receivable_id = fields.Many2one('account.account.template', string='Receivable Account', oldname="property_account_receivable")
    property_account_payable_id = fields.Many2one('account.account.template', string='Payable Account', oldname="property_account_payable")
    property_account_expense_id = fields.Many2one('account.account.template', string='Expense Account on Product Template', oldname="property_account_expense")
    property_account_income_id = fields.Many2one('account.account.template', string='Income Account on Product Template', oldname="property_account_income")
    
    @api.model
    def default_get(self, fields):
        context = self._context or {}
        res = super(WizardMultiChartsAccounts, self).default_get(fields)
        tax_templ_obj = self.env['account.tax.template']
        account_chart_template = self.env['account.chart.template']
        chart_templates = account_chart_template.search([('visible', '=', True)])
        if chart_templates:
            #in order to set default chart which was last created set max of ids.
            chart_id = max(chart_templates.ids)
            if context.get("default_charts"):
                model_data = self.env['ir.model.data'].search_read([('model', '=', 'account.chart.template'), ('module', '=', context.get("default_charts"))], ['res_id'])
                if model_data:
                    chart_id = model_data[0]['res_id']
            chart = account_chart_template.browse(chart_id)
            chart_hierarchy_ids = self._get_chart_parent_ids(chart)
            tax_group = self.env['account.tax.group'].search([('code', '=', '2'), ('type', '=', 'iva')])
            if 'sale_tax_id' in fields:
                sale_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids), ('form_code_ats', '=', '2'),
                                                              ('type_tax_use', '=', 'sale'), ('tax_group_id', '=', tax_group.id)], limit=1, order='sequence')
                res.update({'sale_tax_id': sale_tax and sale_tax.id or False})
            if 'purchase_tax_id' in fields:
                purchase_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids), ('form_code_ats', '=', '2'),
                                                                  ('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', tax_group.id)], limit=1, order='sequence')
                res.update({'purchase_tax_id': purchase_tax and purchase_tax.id or False})
        return res
        
    
    @api.model
    def _get_default_bank_account_ids(self):
        pass


    @api.multi
    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        pass


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    active = fields.Boolean(default=True, help="Set active to false to hide the record without removing it.")
    agent = fields.Boolean(string='Agent Withhold', help='Activate the withholding agent option.')
    option = fields.Selection(selection=[('micro', 'Micro Businesses'),
                                         ('rimpe', 'RIMPE')], string='Presentation in XML', default='micro',
                                         help='In the XML electronic vouchers the legends were added.')
