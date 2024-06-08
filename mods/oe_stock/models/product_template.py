# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    allow_negative_stock = fields.Boolean(string='Allow Negative Stock',
        help="Allow negative stock levels for the stockable products "
        "attached to this category. The options doesn't apply to products "
        "attached to sub-categories of this category.")

class ProductProduct(models.Model):
    _inherit = "product.product"


class ProductTemplate(models.Model):
    _inherit = 'product.template'


    case_method = fields.Selection([
        ('average', 'Average Cost (AVCO)'),
        ('last_cost', 'Last Cost'),
        ('standard', 'Standard Price'),
        ], string='Costing Method', default='standard', required=True,
        help="""Average Cost (AVCO): The products are valued at weighted average cost.
        Last Cost: Last purchase price to date.
        Standard Price: The products are valued at their standard cost defined on the product.""")
    allow_negative_stock = fields.Boolean(string='Allow Negative Stock',
        help="If this option is not active on this product nor on its "
        "product category and that this product is a stockable product, "
        "then the validation of the related stock moves will be blocked if "
        "the stock level becomes negative with the stock move.")
    type = fields.Selection(default='product')
    quant_history_ids = fields.One2many('stock.quant.history', 'product_id', string='History of physical products')
