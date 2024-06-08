#
# @Author: KSOLVES India Private Limited
# @Email: sales@ksolves.com
#


from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    show_qtys = fields.Boolean(string = 'Display Stock of products in POS', default=True)
    limit_qty = fields.Integer(string='Minimum Limit to change the stock color for the product', default=0)
    allow_out_of_stock = fields.Boolean(string = 'Allow Order when Product is Out Of Stock', default=False)