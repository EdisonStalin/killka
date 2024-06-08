# -*- coding: utf-8 -*-

from odoo import models, fields


class Partner(models.Model):
    _inherit = 'res.partner'

    driver = fields.Boolean('Driver', help="The person is driver")

