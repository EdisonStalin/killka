# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    module_oe_pos_mrp = fields.Boolean("Enable Order Production", 
                                       help='Install the oe Make MRP orders from POS module to process the orders')
    