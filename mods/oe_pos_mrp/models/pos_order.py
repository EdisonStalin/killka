# -*- coding: utf-8 -*-

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    mrp_production_id = fields.Many2one('mrp.production', string='MRP Production', readonly=True)
    to_make_mrp = fields.Boolean(related='product_id.to_make_mrp')
    