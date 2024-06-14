# -*- coding: utf-8 -*-

import logging

from psycopg2 import sql, DatabaseError

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round


_logger = logging.getLogger(__name__)


TYPE_STATEMENT = [
    ('sum_locker', 'Sum Locker'),
    ('sum_lines', 'Sum Lines'),
    ('generated_tax', 'Generated Tax'),
    ('total_amount', 'Total Amount'),
]

TYPE_DOCUMENT = [
    ('out_invoice','Customer Invoice'),
    ('in_invoice','Vendor Bill'),
    ('out_refund','Customer Credit Note'),
    ('in_refund','Vendor Credit Note'),
    ('out_settlement','Tax settlement'),
    ('withholding','Withholding'),
    ('out_withholding','Customer Withholding'),
    ('in_withholding','Vendor Withholding'),
]


class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    sequence = fields.Integer(help='Used to order Journals in the dashboard view', default=10)
    statement_line_id = fields.Many2one('statement.form.line', string='Statement Line', ondelete='cascade', index=True)
    form_id = fields.Many2one('statement.form', string='Statement')
    type = fields.Selection(selection=TYPE_STATEMENT, copy=True)
    document_type = fields.Selection(selection=TYPE_DOCUMENT, string='Type Document', copy=True)
    tax_report_line_ids = fields.Many2many(string="Tax Report Lines", comodel_name='account.tax.report.line', relation='account_tax_report_line_tags_rel', help="The tax report lines using this tag")
    tax_negate = fields.Boolean(string="Negate Tax Balance", help="Check this box to negate the absolute value of the balance of the lines associated with this tag in tax report computation.")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="Country for which this tag is available, when applied on taxes.")


    @api.model
    def _get_tax_tags(self, tag_name, country_id):
        """ Returns all the tax tags corresponding to the tag name given in parameter
        in the specified country.
        """
        escaped_tag_name = tag_name.replace('\\', '\\\\').replace('%', '\%').replace('_', '\_')
        return self.env['account.account.tag'].search([('name', '=like', '_' + escaped_tag_name), ('country_id', '=', country_id), ('applicability', '=', 'taxes')])

    @api.constrains('country_id', 'applicability')
    def _validate_tag_country(self):
        for record in self:
            if record.applicability == 'taxes' and not record.country_id:
                raise ValidationError(_("A tag defined to be used on taxes must always have a country set."))

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('document_type'):
            args += [('document_type', '=', context.get('document_type'))]
        return super(AccountAccountTag, self).search(args, offset, limit, order=order, count=count)


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'
    
    code = fields.Integer('Code')
    type = fields.Selection([('iva', 'IVA'),
        ('iva0', 'IVA0'),
        ('ice', 'ICE'),
        ('renta', 'RENTA'),
        ('renta_iva', 'RENTA (Apply IVA)'),
        ('irbpnr', 'IRBPNR'),
        ('isd', 'ISD'),
        ('nobiva', 'No Object IVA'),
        ('exiva', 'No Apply IVA'),
        ('other', 'OTHER'),], 'Type', default='iva')
    active = fields.Boolean(default=True, help="Set active to false to hide the tax group without removing it.")

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            if record.code:
                res.append((record.id, '[%s] %s' % (record.code, record.name)))
            else:
                res.append((record.id, record.name))
        return res

class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    type_tax_use = fields.Selection(selection_add=[('all', 'All')])
    form_code_ats = fields.Char('Form code anexo', size=6, help='Unique code anexo (ATS) related to the tax')
    code_form_id = fields.Many2one('account.account.tag', string='Tax Settlement')
    refund_code_form_id = fields.Many2one('account.account.tag', string='Tax Settlement')
    code_applied_id = fields.Many2one('account.account.tag', string='Tax Settlement Applied')
    module = fields.Selection([('pay_res', _('Payments to residents')), 
                               ('pay_no_res', _('payments to non-residents'))], 'Module', help="Concepts of retention in the source of income tax (AIR)")
    invoice_repartition_line_ids = fields.One2many(string="Distribution for Invoices", comodel_name="account.tax.repartition.line", inverse_name="invoice_tax_id", copy=True, help="Distribution when the tax is used on an invoice")
    refund_repartition_line_ids = fields.One2many(string="Distribution for Refund Invoices", comodel_name="account.tax.repartition.line", inverse_name="refund_tax_id", copy=True, help="Distribution when the tax is used on a refund")


    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('ALTER TABLE "account_tax" DROP CONSTRAINT IF EXISTS "account_tax_name_company_uniq"')


    """@api.one
    @api.constrains('name', 'company_id', 'type_tax_use', 'amount')
    def _check_number(self):
        domain = [('name', '=', self.name), ('company_id', '=', self.company_id.id), ('type_tax_use', '=', self.type_tax_use), ('amount', '=', self.amount)]
        unique_tax = self.search(domain)
        for x in unique_tax:
            if x.id != self.id: raise UserError(_('Tax names must be unique!'))"""


    @api.constrains('invoice_repartition_line_ids', 'refund_repartition_line_ids')
    def _validate_repartition_lines(self):
        pass
        """for record in self:
            invoice_repartition_line_ids = record.invoice_repartition_line_ids.sorted()
            refund_repartition_line_ids = record.refund_repartition_line_ids.sorted()
            record._check_repartition_lines(invoice_repartition_line_ids)
            record._check_repartition_lines(refund_repartition_line_ids)

            if len(invoice_repartition_line_ids) != len(refund_repartition_line_ids):
                raise ValidationError(_("Invoice and credit note distribution should have the same number of lines."))

            index = 0
            while index < len(invoice_repartition_line_ids):
                inv_rep_ln = invoice_repartition_line_ids[index]
                ref_rep_ln = refund_repartition_line_ids[index]
                if inv_rep_ln.repartition_type != ref_rep_ln.repartition_type or inv_rep_ln.factor_percent != ref_rep_ln.factor_percent:
                    raise ValidationError(_("Invoice and credit note distribution should match (same percentages, in the same order)."))
                index += 1"""


    @api.model
    def default_get(self, fields_list):
        # company_id is added so that we are sure to fetch a default value from it to use in repartition lines, below
        rslt = super(AccountTax, self).default_get(fields_list + ['company_id'])

        company_id = rslt.get('company_id')
        company = self.env['res.company'].browse(company_id)

        if 'refund_repartition_line_ids' in fields_list:
            # We write on the related country_id field so that the field is recomputed. Without that, it will stay empty until we save the record.
            rslt['refund_repartition_line_ids'] = [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'tax_fiscal_country_id': company.country_id.id}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'tax_fiscal_country_id': company.country_id.id}),
            ]

        if 'invoice_repartition_line_ids' in fields_list:
            # We write on the related country_id field so that the field is recomputed. Without that, it will stay empty until we save the record.
            rslt['invoice_repartition_line_ids'] = [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'tax_fiscal_country_id': company.country_id.id}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'tax_fiscal_country_id': company.country_id.id}),
            ]

        return rslt


    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('type'):
            if context.get('type') == 'out_withholding':
                args += [('type_tax_use', '=', 'purchase')]
            elif context.get('type') == 'in_withholding':
                args += [('type_tax_use', '=', 'sale')]

        if context.get('journal_id'):
            journal = self.env['account.journal'].browse(context.get('journal_id'))
            if journal.type in ('sale', 'purchase'):
                args += ['|', ('type_tax_use', 'in', [journal.type, 'all'])]
        return super(AccountTax, self).search(args, offset, limit, order='sequence desc', count=count)


    @api.model
    def name_search(self, name, args=[], operator='ilike', limit=100):
        context = self._context or {}
        if context.get('import_file', False): args = []
        if len(name): args += ['|', ('name', operator, name), ('form_code_ats', operator, name + '%')]
        if context.get('type'):
            args += ['|', ('type_tax_use','=','all')]
        recs = self.search(args, limit=limit)
        return recs.name_get()


    @api.multi
    def name_get(self):
        res = []
        for record in self:
            if record.tax_group_id.type in ['renta', 'renta_iva', 'ice']:
                if not record.form_code_ats:
                    res.append((record.id, record.name))
                else:
                    res.append((record.id, '[%s] %s' % (record.form_code_ats, record.name)))
            else:
                res.append((record.id, record.name))
        return res


    def _increase_rank(self, field, n=1):
        if self.ids and field in ['sequence']:
            try:
                with self.env.cr.savepoint():
                    query = sql.SQL("""
                        SELECT {field} FROM account_tax WHERE ID IN %(tax_ids)s FOR UPDATE NOWAIT;
                        UPDATE account_tax SET {field} = {field} + %(n)s
                        WHERE id IN %(tax_ids)s
                    """).format(field=sql.Identifier(field))
                    self.env.cr.execute(query, {'tax_ids': tuple(self.ids), 'n': n})
            except DatabaseError as e:
                if e.pgcode == '55P03':
                    _logger.debug('Another transaction already locked partner rows. Cannot update partner ranks.')
                else:
                    raise e

    def _get_form_tag(self, tag_ids):
        for tag in tag_ids:
            tag_list = tag.name.split("_")
            form = tag_list[0]
            locker = tag_list[1]
        form_id = self.env['statement.form'].search([('code','=',form)])
        return form, locker

    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        """ Returns all information required to apply taxes (in self + their children in case of a tax goup).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order as sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }]
        } """
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        prec = currency.decimal_places

        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company_id.tax_calculation_rounding_method == 'round_globally' else True
        round_total = True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])
            round_total = bool(self.env.context['round'])

        if not round_tax:
            prec += 5

        base_values = self.env.context.get('base_values')
        if not base_values:
            total_excluded = total_included = base = round(price_unit * quantity, prec)
        else:
            total_excluded, total_included, base = base_values

        # Sorting key is mandatory in this case. When no key is provided, sorted() will perform a
        # search. However, the search method is overridden in account.tax in order to add a domain
        # depending on the context. This domain might filter out some taxes from self, e.g. in the
        # case of group taxes.
        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                children = tax.children_tax_ids.with_context(base_values=(total_excluded, total_included, base))
                ret = children.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['base'] if tax.include_base_amount else base
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue

            tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner)
            if not round_tax:
                tax_amount = round(tax_amount, prec)
            else:
                tax_amount = float_round(tax_amount, precision_digits=prec)

            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount

            # Keep base amount used for the current tax
            tax_base = base

            if tax.include_base_amount:
                base += tax_amount

            taxes.append({
                'id': tax.id,
                'type': tax.tax_group_id.type,
                'name': tax.with_context(**{'lang': partner.lang} if partner else {}).name,
                'amount': tax_amount,
                'base': tax_base,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
                'price_include': tax.price_include,
                'tax_exigibility': tax.tax_exigibility,
            })

        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': float_round(total_excluded, precision_digits=prec) if round_total else total_excluded,
            'total_included': float_round(total_included, precision_digits=prec) if round_total else total_included,
            'base': base,
        }


class AccountTaxRepartitionLine(models.Model):
    _name = "account.tax.repartition.line"
    _description = "Tax Repartition Line"
    _order = 'sequence, repartition_type, id'
    _check_company_auto = True

    factor_percent = fields.Float(string="%", required=True, help="Factor to apply on the account move lines generated from this distribution line, in percents")
    factor = fields.Float(string="Factor Ratio", compute="_compute_factor", help="Factor to apply on the account move lines generated from this distribution line")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    account_id = fields.Many2one(string="Account",
        comodel_name='account.account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('internal_type', 'not in', ('receivable', 'payable'))]",
        check_company=True,
        help="Account on which to post the tax amount")
    tag_ids = fields.Many2many(string="Tax Grids", comodel_name='account.account.tag', domain=[('applicability', '=', 'taxes')], copy=True)
    invoice_tax_id = fields.Many2one(comodel_name='account.tax',
        ondelete='cascade',
        check_company=True,
        help="The tax set to apply this distribution on invoices. Mutually exclusive with refund_tax_id")
    refund_tax_id = fields.Many2one(comodel_name='account.tax',
        ondelete='cascade',
        check_company=True,
        help="The tax set to apply this distribution on refund invoices. Mutually exclusive with invoice_tax_id")
    tax_id = fields.Many2one(comodel_name='account.tax', compute='_compute_tax_id')
    tax_fiscal_country_id = fields.Many2one(string="Fiscal Country", comodel_name='res.country', related='company_id.country_id', help="Technical field used to restrict tags domain in form view.")
    company_id = fields.Many2one(string="Company", comodel_name='res.company', compute="_compute_company", store=True, help="The company this distribution line belongs to.")
    sequence = fields.Integer(string="Sequence", default=1,
        help="The order in which distribution lines are displayed and matched. For refunds to work properly, invoice distribution lines should be arranged in the same order as the credit note distribution lines they correspond to.")
    use_in_tax_closing = fields.Boolean(string="Tax Closing Entry")

    @api.onchange('account_id', 'repartition_type')
    def _on_change_account_id(self):
        if not self.account_id or self.repartition_type == 'base':
            self.use_in_tax_closing = False
        else:
            self.use_in_tax_closing = self.account_id.internal_type not in ('income', 'expense')

    @api.constrains('invoice_tax_id', 'refund_tax_id')
    def validate_tax_template_link(self):
        for record in self:
            if record.invoice_tax_id and record.refund_tax_id:
                raise ValidationError(_("Tax distribution lines should apply to either invoices or refunds, not both at the same time. invoice_tax_id and refund_tax_id should not be set together."))

    @api.depends('factor_percent')
    def _compute_factor(self):
        for record in self:
            record.factor = record.factor_percent / 100.0

    @api.depends('invoice_tax_id.company_id', 'refund_tax_id.company_id')
    def _compute_company(self):
        for record in self:
            record.company_id = record.invoice_tax_id and record.invoice_tax_id.company_id.id or record.refund_tax_id.company_id.id

    @api.depends('invoice_tax_id', 'refund_tax_id')
    def _compute_tax_id(self):
        for record in self:
            record.tax_id = record.invoice_tax_id or record.refund_tax_id

    @api.onchange('repartition_type')
    def _onchange_repartition_type(self):
        if self.repartition_type == 'base':
            self.account_id = None

    