# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    order_id = fields.Many2one('pos.order', string='Origin POS order', help='Origin POS Order.')
    create_order_id = fields.Many2one('pos.order', string='Create POS order', help='Create POS Order.')

    @api.multi
    def unlink(self):
        if self.order_id:
            self.order_id.write({'state': 'done'})
        return super(AccountInvoice, self).unlink()
