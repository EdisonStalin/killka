# -*- coding: utf-8 -*-

from odoo import models, fields
   

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    not_view_pos = fields.Boolean(related='pos_categ_id.not_view_pos')
    not_sale = fields.Boolean(string='Do not sales',
        help='The marked product will not be included in sales for billing.')
