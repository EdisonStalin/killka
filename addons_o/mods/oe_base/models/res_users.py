# -*- coding: utf-8 -*-

from odoo import models, api


class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        user = super(Users, self).create(vals)
        user.partner_id.customer = False
        return user

    @api.multi
    def _is_admin(self):
        self.ensure_one()
        return self._is_superuser() or self.has_group('base.group_erp_manager') or self.has_group('oe_base.group_admin')
    
