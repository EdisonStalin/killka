# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api


class AccountWithholdingReport(models.Model):
    _name = "account.withholding.report"
    _description = "Withholding Statistics"
    _auto = False
    _rec_name = 'date'

    @api.multi
    @api.depends('currency_id', 'date', 'price_total', 'price_average', 'residual')
    def _compute_amounts_in_user_currency(self):
        """Compute the amounts in the currency of the user
        """
        context = dict(self._context or {})
        user_currency_id = self.env.user.company_id.currency_id
        currency_rate_id = self.env['res.currency.rate'].search([
            ('rate', '=', 1),
            '|', ('company_id', '=', self.env.user.company_id.id), ('company_id', '=', False)], limit=1)
        base_currency_id = currency_rate_id.currency_id
        ctx = context.copy()
        for record in self:
            ctx['date'] = record.date
            record.user_currency_price_total = base_currency_id.with_context(ctx).compute(record.price_total, user_currency_id)
            record.user_currency_price_average = base_currency_id.with_context(ctx).compute(record.price_average, user_currency_id)
            record.user_currency_residual = base_currency_id.with_context(ctx).compute(record.residual, user_currency_id)

    date = fields.Date(readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_qty = fields.Float(string='Product Quantity', readonly=True)
    uom_name = fields.Char(string='Reference Unit of Measure', readonly=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', string='Partner Company', help="Commercial Entity")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    price_total = fields.Float(string='Total Without Tax', readonly=True)
    user_currency_price_total = fields.Float(string="Total Without Tax", compute='_compute_amounts_in_user_currency', digits=0)
    price_average = fields.Float(string='Average Price', readonly=True, group_operator="avg")
    user_currency_price_average = fields.Float(string="Average Price", compute='_compute_amounts_in_user_currency', digits=0)
    currency_rate = fields.Float(string='Currency Rate', readonly=True, group_operator="avg", groups="base.group_multi_currency")
    nbr = fields.Integer(string='# of Lines', readonly=True)  # TDE FIXME master: rename into nbr_lines
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
        ], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled')
        ], string='Invoice Status', readonly=True)
    date_due = fields.Date(string='Due Date', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True, domain=[('deprecated', '=', False)])
    account_line_id = fields.Many2one('account.account', string='Account Line', readonly=True, domain=[('deprecated', '=', False)])
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account', readonly=True)
    residual = fields.Float(string='Due Amount', readonly=True)
    user_currency_residual = fields.Float(string="Total Residual", compute='_compute_amounts_in_user_currency', digits=0)
    country_id = fields.Many2one('res.country', string='Country of the Partner Company')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', groups="analytic.group_analytic_accounting")

    _order = 'date desc'