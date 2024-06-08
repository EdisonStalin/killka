#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.osv import expression


class AccountTaxSupport(models.Model):

    _name = 'account.tax.support'
    _description = "Tax support"
    _order = "id asc"
    
    code = fields.Char('Support code', size=3, required=True, copy=False, help="Reference tax support")
    name = fields.Char('Tax Support', size=150, copy=True, required=True)
    document_ids = fields.Many2many('account.type.document', string='Document Type', help="Relation de document type")
    active = fields.Boolean('Active', default=True, help="Set active to false to hide the tax support without removing it")
    
    _sql_constraints = [
        ('name_type_uniq', 'unique(code, name)', 'Type and code names must be unique'),
    ]
    
    @api.multi
    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, '%s - %s' % (record.code, record.name)))
        return res
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', '=' + operator, name + '%')]
        recs = self.search(expression.AND([domain, args]), limit=limit)
        return recs.name_get()

