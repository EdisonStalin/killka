# -*- coding: utf-8 -*-

import logging

from odoo import models, api, fields, _

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    #form_id = fields.Many2one('statement.form', related='code_form_id.form_id')
    #form_line_id = fields.Many2one('statement.form.line', related='code_form_id.statement_line_id')
