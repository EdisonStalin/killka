# -*- coding: utf-8 -*-

import math

from odoo import api, fields, models, tools


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    display_rounding = fields.Float('Display Rounding Factor', digits=(12, 6))
    display_decimal_places = fields.Integer(compute='_get_display_decimal_places')

    @api.one
    @api.depends('rounding', 'display_rounding')
    def _get_display_decimal_places(self):
        if not self.display_rounding:
            self.display_decimal_places = self.decimal_places
        elif 0 < self.display_rounding < 1:
            self.display_decimal_places = \
                int(math.ceil(math.log10(1 / self.display_rounding)))
        else:
            self.display_decimal_places = 0

    @api.multi
    def round(self, amount):
        """Return ``amount`` rounded  according to ``self``'s rounding rules.

           :param float amount: the amount to round
           :return: rounded float
        """
        # TODO: Need to check why it calls round() from sale.py, _amount_all() with *No* ID after below commits,
        # https://github.com/odoo/odoo/commit/36ee1ad813204dcb91e9f5f20d746dff6f080ac2
        # https://github.com/odoo/odoo/commit/0b6058c585d7d9a57bd7581b8211f20fca3ec3f7
        # Removing self.ensure_one() will make few test cases to break of modules event_sale, sale_mrp and stock_dropshipping.
        # self.ensure_one()
        round_tax = False
        digits = 2
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])
            digits = self.env.context['digits']
        if round_tax:
            return tools.float_round(amount, precision_digits=digits)
        else:
            return tools.float_round(amount, precision_rounding=self.rounding)
