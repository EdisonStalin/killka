# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.osv import expression


class AccountTypeDocument(models.Model):

    _name = 'account.type.document'
    _description = "Type of authorized document"
    _order = "id asc"
    
    code = fields.Char('Document code', size=3, required=True, copy=False, help="Reference type the document")
    name = fields.Char('Document name', size=150, copy=True, required=True)
    short_name = fields.Char(string='Short Name', size=100, copy=True)
    is_electronic = fields.Boolean('Is electronic', copy=True, help="Authorization type check")
    code_doc_xml = fields.Char('Code of xml', size=3, copy=False, help="Code used in tag codDoc in electronic document")
    is_refund = fields.Boolean(copy=True, help='It is a refund type document')
    type = fields.Selection([('in', _('Inbound')), ('out', _('Outbound')), ('both', _('Both of them'))], 'Type', default='in', help='Document type')
    active = fields.Boolean('Active', default=True, help="Set active to false to hide the type document without removing it")
    
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


