# -*- coding: utf-8 -*-

from odoo import models, api, fields


class Bank(models.Model):
    _inherit = 'res.bank'
    
    code = fields.Char(atring='Bank Code', size=4)
    cup = fields.Float(string='% Cup', digits=(8, 4), default=0.0, required=True, copy=False)
