# -*- coding: utf-8 -*-

from odoo import models, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    @api.model
    def create(self, vals):
        if 'journal_id' in vals:
            vals['method_id'] = self.env['account.journal'].browse(vals['journal_id']).method_id.id
        res = super(AccountPayment, self).create(vals)
        res._onchange_partner()
        return res