# -*- coding: utf-8 -*-

from odoo import models, api


class AccountAuthorization(models.Model):
    _inherit = 'account.authorization'

    @api.multi
    def generation_access_key(self, name, type_doc, date_doc, env='1'):
        company = self.env.user.company_id
        if company.environment == 'prod': env = '2'
        return super(AccountAuthorization, self).generation_access_key(name, type_doc, date_doc, env)
