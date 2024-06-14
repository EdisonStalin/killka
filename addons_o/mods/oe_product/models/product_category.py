# -*- coding: utf-8 -*-

from odoo import models, api, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    name = fields.Char('Name', index=True, required=True, translate=False)
    prefix = fields.Char(string='Prefix', size=5, help="Prefix value of the record for the sequence")
    active = fields.Boolean(string='Active', default=True,
        help="If unchecked, it will allow you to hide the category without removing it.")
    
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(ProductCategory, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('prefix', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('category_code'):
            args += [('prefix','=',context.get('category_code'))]
        return super(ProductCategory, self).search(args, offset, limit, order='name ASC', count=count)
