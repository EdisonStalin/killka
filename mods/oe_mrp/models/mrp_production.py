# -*- coding: utf-8 -*-

import logging

from odoo import models, api

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    @api.model
    def create(self, values):
        production = super(MrpProduction, self).create(values)
        if production.availability != 'none':
            production.action_assign()
        return production
