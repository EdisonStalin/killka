# -*- coding: utf-8 -*-
# Part of AppEcuaOnline. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    main_warehouse_id = fields.Many2one('stock.warehouse', related='company_id.main_warehouse_id', string='Main Warehouse', help='Main warehouse where materials are unloaded.')
    residual_warehouse_id = fields.Many2one('stock.warehouse', related='company_id.residual_warehouse_id', string=' Residual Warehouse', help='Warehouse of surplus or waste.')

