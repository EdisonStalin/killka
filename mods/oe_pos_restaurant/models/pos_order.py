# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'
