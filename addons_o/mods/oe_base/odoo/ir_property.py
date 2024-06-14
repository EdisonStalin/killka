# -*- coding: utf-8 -*-

from odoo import models, api


class Property(models.Model):
    _inherit = 'ir.property'

    @api.model
    def default_get(self, fields):
        res = super(Property, self).default_get(fields)
        if res.get('fields_id', False):
            ir_model_field = self.env['ir.model.fields'].browse(res['fields_id'])
            res['name'] = ir_model_field.field_description
        return res

