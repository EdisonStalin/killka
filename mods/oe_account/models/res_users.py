# -*- coding: utf-8 -*-

from odoo import models, fields


class Users(models.Model):
    
    _inherit = 'res.users'
    
    authorization_ids = fields.Many2many('account.authorization', 'res_authorization_users_rel', 'user_id', 'aid',
        string='Authorizations', domain=[('is_electronic', '=', True), ('type', '=', 'internal')], help='Assigns the internal authorizations allowed to the user')
    
    