# -*- coding: utf-8 -*-

from odoo import models, api, fields, _


class Color(models.Model):
    _name = 'ir.color'
    _description = 'Color'
    _order = 'name, id'
    
    name = fields.Char(string='Name Color', size=50, required=True)
    color_hex = fields.Char(string='Value Hex', size=7)
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', _('Color already exists')),
    ]
    
    @api.model
    def create(self, vals):
        if 'name' in vals:
            vals['name'] = vals['name'].upper()
        return super(Color, self).create(vals)
    
    @api.multi
    def write(self, vals):
        if 'name' in vals:
            vals['name'] = vals['name'].upper()
        return super(Color, self).write(vals)
    
