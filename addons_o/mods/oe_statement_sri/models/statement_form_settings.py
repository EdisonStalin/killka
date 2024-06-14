# -*- coding: utf-8 -*-

from odoo import models, api, fields, _

TYPE_TAX = [('iva', 'IVA'),
    ('iva0', 'IVA0'),
    ('ice', 'ICE'),
    ('renta', 'RENTA'),
    ('renta_iva', 'RENTA (Apply IVA)'),
    ('irbpnr', 'IRBPNR'),
    ('isd', 'ISD'),
    ('nobiva', 'No Object IVA'),
    ('exiva', 'No Apply IVA'),
    ('other', 'OTHER'),
]


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
]


class StatementForm(models.Model):
    _name = "statement.form"
    _description = 'Statement Form'

    
    name = fields.Char(string='Document name', size=250, copy=True, required=True)
    description = fields.Text(string='Reference', copy=True)
    sequence = fields.Integer(default=1, help="Gives the sequence of this line when displaying the statement.")
    type_period = fields.Selection([('monthly', 'Month'), ('yearly', 'Year')],
        default='monthly', string='Period', help="Specify Interval for form generation.")
    active = fields.Boolean(default=True, help="Set active to false to hide the type document without removing it")
    context = fields.Char(string='Context Value', default={}, required=True,
        help="Context dictionary as Python expression, empty by default (Default: {})")
    line_ids = fields.One2many('statement.form.line', 'form_id', string='Lines Codes', copy=True)
    action_id = fields.Many2one('ir.actions.act_window', string='Window Action', required=True, copy=True)


    _sql_constraints = [
        ('name_type_uniq', 'unique(name)', 'Statement Line names must be unique'),
    ]


    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(name=_("%s (copy)") % (self.name or ''))
        return super(StatementForm, self).copy(default)


    @api.model
    def create(self, vals):
        if 'name' in vals: vals['name'] = vals['name'].upper()
        return super(StatementForm, self).create(vals)
    
    
    @api.multi
    def write(self, vals):
        if 'name' in vals: vals['name'] = vals['name'].upper()
        return super(StatementForm, self).write(vals)


class StatementFormLine(models.Model):
    _name = "statement.form.line"
    _description = 'Statement Form Line'

    
    name = fields.Char(string='Document name', size=250, copy=True, required=True)
    sequence = fields.Integer(default=1, help="Gives the sequence of this line when displaying the statement.", copy=True)
    active = fields.Boolean(default=True, help="Set active to false to hide the type document without removing it")
    form_id = fields.Many2one('statement.form', string='Statement Form', ondelete='cascade', index=True)
    parent_id = fields.Many2one('statement.form.line', string='Statement Line', copy=True)
    line_code_ids = fields.One2many('account.account.tag', 'statement_line_id', string='Lines Codes', copy=True)
    total_check = fields.Boolean(string='Total Apply', copy=True, help='Result total of other line')
    fixed_asset = fields.Boolean(string='Check Fixed Asset', copy=True, help='Product represents as a fixed asset')
    service = fields.Boolean(string='Check Service', copy=True, help='Product represents as a service')
    goods = fields.Boolean(string='Check Goods', copy=True, help='Product represents as a goods')
    tributary_credit = fields.Boolean(string='Check Tributary Credit', copy=True, help='The tax with tax credit applies or not')
    type_tax = fields.Selection(selection=TYPE_TAX, string='Tax Type', copy=True, help='Type of tax you are applying')
    
    _sql_constraints = [
        ('name_type_uniq', 'unique(name, form_id)', 'Statement Line names must be unique'),
    ]


    @api.model
    def create(self, vals):
        if 'name' in vals:
            vals['name'] = vals['name'].upper()
        return super(StatementFormLine, self).create(vals)
    
    
    @api.multi
    def write(self, vals):
        if 'name' in vals:
            vals['name'] = vals['name'].upper()
        return super(StatementFormLine, self).write(vals)


class StatementFormLineCode(models.Model):
    _inherit = "account.account.tag"

    statement_line_id = fields.Many2one('statement.form.line', string='Statement Line', ondelete='cascade', index=True)
    form_id = fields.Many2one('statement.form', related='statement_line_id.form_id', store=True)

