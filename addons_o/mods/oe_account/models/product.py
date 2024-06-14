# -*- coding: utf-8 -*-

from odoo import models, api, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', string='Customer Taxes',
        domain=[('type_tax_use', 'in', ['sale', 'all'])])
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id', string='Vendor Taxes',
        domain=[('type_tax_use', 'in', ['purchase', 'all'])])

    @api.model
    def default_get(self, default_fields):
        company_id = self.env.user.company_id
        res = super(ProductTemplate, self).default_get(default_fields)
        if company_id.property_account_income_id:
            res['property_account_income_id'] = company_id.property_account_income_id.id or False
        if company_id.property_account_expense_id:
            res['property_account_expense_id'] = company_id.property_account_expense_id.id or False
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def _convert_prepared_anglosaxon_line(self, line, partner):
        vals = super(ProductProduct, self)._convert_prepared_anglosaxon_line(line, partner)
        vals.update({
            'tax_tag_ids': line.get('tax_tag_ids', [])
        })
        return vals
    
