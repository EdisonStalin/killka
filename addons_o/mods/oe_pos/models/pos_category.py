# -*- coding: utf-8 -*-

from odoo import models, fields


class PosCategory(models.Model):
    _inherit = 'pos.category'
    
    not_view_pos = fields.Boolean(string='Not view POS', help='Do not show as part of the POS categories')
    
    