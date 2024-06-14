# -*- coding: utf-8 -*-

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    main_warehouse_id = fields.Many2one('stock.warehouse', string='Main Warehouse', help='Main warehouse where materials are unloaded.')
    residual_warehouse_id = fields.Many2one('stock.warehouse', string=' Residual Warehouse', help='Warehouse of surplus or waste.')
