# -*- coding: utf-8 -*-

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

class RestaurantPrinter(models.Model):
    _inherit = "restaurant.printer"

    physical_printer = fields.Boolean(
        default=False,
        string="Physical Printer",
        help="Check this box if this printer is Physical printer",
    )
    