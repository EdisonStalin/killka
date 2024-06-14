# -*- coding: utf-8 -*-

from odoo import models, api, fields

class AccountAccount(models.Model):
    _inherit = 'account.account'


    form_id = fields.Many2one('statement.form', string='Statement Form')
    form_line_id = fields.Many2one('statement.form.line', string='Statement Form Line')
    code_form_id = fields.Many2one('statement.form.line.code', string='Tax Settlement')
