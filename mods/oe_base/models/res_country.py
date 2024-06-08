# -*- coding: utf-8 -*-

from odoo import models, api


class CountryState(models.Model):
    _inherit = 'res.country.state'
    
    _sql_constraints = [
        ('name_code_uniq', 'unique(country_id, name, code)', 'The code of the state must be unique by country !')
    ]
    
    @api.model
    def create(self, vals):
        if vals.get('name'):
            vals['name'] = vals['name'].capitalize()
        return super(CountryState, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('name'):
            vals['name'] = vals['name'].capitalize()
        return super(CountryState, self).write(vals)
    
