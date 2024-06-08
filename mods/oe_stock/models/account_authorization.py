# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductTemplate(models.Model):
    _name  = "account.authorization"
    _inherit = 'account.authorization'
    

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', help="This will determine picking type of incoming shipment")