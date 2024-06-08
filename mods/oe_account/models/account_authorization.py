# -*- coding: utf-8 -*-

import logging
import random

from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_MODULO_11 = {
    'BASE' : 11,
    'FACTOR' : 2,
    'RETORNO11' : 0,
    'RETORNO10' : 1,
    'PESO' : 2,
    'MAX_WEIGHT' : 7,
}

class AccountAuthorization(models.Model):
    _name = 'account.authorization'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Authorization"
    _order = "id desc"

    
    name = fields.Char(string='Authorization', size=10, copy=True, default='9999999999')
    entity = fields.Char(string='Entity', size=3, required=True, default=lambda self: self.env.user.company_id.code_business, copy=True, help="Establishment point")
    issue = fields.Char(string='Issue', size=3, required=True, default='000', copy=True, hep="Point of emission of the establishment")
    check_start = fields.Boolean(string='Check Start', help='Enable the sequential start, otherwise follow the normal sequence.')
    number_since = fields.Integer(string='N° since', required=True, default=1, copy=False, help="Physical authorization start number")
    number_to = fields.Integer(string='N° to', required=True, default=999999999, copy=False, help="Number where the physical authorization ends")
    expires = fields.Date(string='Expires', copy=False, help="Date where the physical authorization ends")
    is_electronic = fields.Boolean('Is electronic', copy=True, help="Authorization type check")
    manual_sequence = fields.Boolean(string='Manual Sequence', default=False, copy=False, help='Enable allows to carry the sequential of the document that is entered manually')
    type_document_id = fields.Many2one('account.type.document', string='Voucher Type', change_default=True, 
                                       domain=[('active', '=', True)], required=True, copy=True, track_visibility='always')
    type = fields.Selection([('external', 'external'), ('internal', 'internal')], 'Type', required=True, copy=True)
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True, required=True, track_visibility='always')
    comment = fields.Text('Additional Information')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    sequence_id = fields.Many2one('ir.sequence', string='Entry Sequence', 
                                  help="This field contains the information related to the numbering of the documents entries of this authorization.", copy=False)
    number_next_actual = fields.Integer(related='sequence_id.number_next_actual')
    active = fields.Boolean(default=True, help="Set active to false to hide the authorization without removing it.")
    establishment_id = fields.Many2one('res.establishment', string='Business Store')
    line_info_ids = fields.One2many('additional.info', 'authorization_id', string='Information Additional Lines', copy=True)


    @api.constrains('name', 'entity', 'issue',  'company_id', 'is_electronic')
    def _check_number(self):
        for auth in self:
            domain = [('company_id', '=', auth.company_id.id), ('type_document_id', '=', auth.type_document_id.id),
                      ('type', '=', auth.type), ('entity','=',auth.entity), ('issue','=',auth.issue),
                      ('partner_id', '=', auth.partner_id.id)]
            if not auth.is_electronic:
                domain += [('name', '=', self.name)]
                if len(auth.name)!=10:
                    raise UserError(_('The physical authorization %s is wrongly entered') % auth.name)
            if len(auth.entity)!=3 or auth.entity == '000':
                raise UserError(_('The entity number of the authorization %s is wrongly entered %s') % (auth.entity, auth.name))
            if len(auth.issue)!=3 or auth.issue == '000':
                raise UserError(_('The issue number of the authorization %s is wrongly entered %s') % (auth.issue, auth.name))
            unique_number = self.search(domain)
            for x in unique_number:
                if x.id != auth.id and x.name == auth.name:
                    raise UserError(_('Authorization must be unique per company!'))


    def _get_info_authorization(self):
        lines_info = []
        for line in self.line_info_ids:
            lines_info.append((0, 0, {
                'sequence': line.sequence,
                'name': line.name,
                'value_tag': line.value_tag,
            }))
        return lines_info

    @api.model
    def default_get(self, fields_list):
        res = super(AccountAuthorization, self).default_get(fields_list)
        if self._context.get('invoice_type', False):
            res['type'] = 'internal' if self._context.get('invoice_type')\
                in ['out_invoice','out_refund','out_withholding'] else 'external'
        if res.get('type', '') == 'internal':
            res['entity'] = self.env.user.company_id.code_business
            res['partner_id'] = self.env.user.company_id.partner_id.id
        return res

    @api.model
    def create(self, vals):
        if 'partner_id' not in vals and self._context.get('default_type') == 'internal':
            vals['partner_id'] = self.env.user.company_id.partner_id.id
        res = super(AccountAuthorization, self).create(vals)
        if not res.manual_sequence:
            res.sequence_id = self._create_sequence(vals).id
        return res

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            if record.establishment_id:
                res.append((record.id, '%s (%s %s)' %
                    (record.name, record.establishment_id.code_business, record.establishment_id.name)))
            else:               
                res.append((record.id, record.name))
        return res

    def _find(self, entity, issue, code_doc, electronic=False, partner_id=False, type_doc='external', establishment_id=False):
        company = self.env.user.company_id
        domain = [('entity','=',entity), ('issue','=',issue), ('company_id', '=', company.id),
                  ('type_document_id.code','=', code_doc), ('is_electronic','=',electronic)]
        if partner_id: domain += [('partner_id','=',partner_id.id), ('type','=',type_doc)]
        if establishment_id: domain += [('establishment_id','=',establishment_id.id)]
        return self.search(domain, order='id ASC', limit=1)
    
    def _create_sequence(self, vals):
        value = {
            'name': '%s %s AE' % (_('Sequence'), vals['name']),
            'implementation': 'no_gap',
            'padding': 9,
            'number_increment': 1,
            'company_id': self.env.user.company_id.id
        }
        if 'check_start' in value: value['number_next_actual'] = value.get('number_since', 1)
        return self.sudo().env['ir.sequence'].create(value)

    @api.multi
    def _set_sequence_next(self, model, status):
        ''' Set the number_next on the sequence related to the invoice/bill/refund'''
        self.ensure_one()
        n_min = self.number_since
        n_max = self.number_to
        sql = """SELECT COALESCE(MAX(internal_number), %s) AS internal_number
            FROM %s WHERE company_id=%s AND authorization_id=%s
            AND state IN %s""" % (n_min, model, self.company_id.id, self.id, status)
        self.env.cr.execute(sql)
        num_max = self.env.cr.fetchone()
        if num_max:
            num_max = int(num_max[0])
            if num_max > self.number_to:
                raise UserError(_('The next number exceeds the authorization number'))
        sql = """SELECT n FROM %s RIGHT JOIN generate_series(%s, %s) AS n 
                ON (internal_number=n AND authorization_id=%s) WHERE internal_number IS NULL LIMIT 1""" % (model, max(num_max - 500, n_min), min(num_max + 500, n_max), self.id)
        self.env.cr.execute(sql)
        num = self.env.cr.fetchone()
        if num is None:
            _logger.critical(_('Within document number search is out of range %s in select %s') % (num_max, sql))
            raise UserError(_('Sequence authorization %s not found.') % self.name)
        if num[0] > n_max or num[0] <= 0:
            raise UserError(_('The next number %s exceeds the authorization limit, create a new authorization.') % num[0])
        if num: self.sequence_id.sudo().write({'number_next': num[0]})
        return True


    @api.onchange('is_electronic', 'establishment_id', 'type_document_id', 'issue', 'type')
    def _onchange_establishment(self):
        res = dict()
        value = dict()
        if self.type == 'internal':
            value['partner_id'] = self.env.user.company_id.partner_id.id
            code_business = self.establishment_id.code_business\
                if self.establishment_id else self.env.user.company_id.code_business
            if not code_business: raise UserError(_('You do not have the company code configured'))
            value['entity'] = code_business
            if self.is_electronic:
                value['number_since'] = 1
                value['number_to'] = 999999999
        else:
            value['manual_sequence'] = True
        if self.is_electronic:
            value['manual_sequence'] = False
            value['name'] = 'AE%s%s%s' % (self.type_document_id.code, self.entity, self.issue)
        elif not self.is_electronic and not self.name:
            value['name'] = '9999999999'
        res.update({'value': value})
        return res


    @api.multi
    def generation_access_key(self, name, type_doc, date_doc, env='1'):
        company = self.env.user.company_id
        ruc = company.partner_id.vat
        if not ruc: raise UserError(_('Enter the company RUC'))
        if not type_doc.code_doc_xml:
            raise UserError(_('The document type %s does not have the code activated') % type_doc.name)
        list_date = date_doc.split('-')
        list_date.reverse()
        new_date = ''.join(list_date)
        number = ''.join(name.split('-'))
        nrandom = str(random.random())[2:10]
        access_key = new_date+type_doc.code_doc_xml+ruc+env+number+nrandom+'1'
        access_key += str(self._compute_mod11(access_key))
        return access_key

    
    def _compute_mod11(self, access_key):
        total = 0
        weight = _MODULO_11['PESO']
        for item in reversed(access_key):
            total += int(item) * weight
            weight += 1
            if weight > _MODULO_11['MAX_WEIGHT']:
                weight = _MODULO_11['PESO']
        mod = 11 - total % _MODULO_11['BASE']
        mod = self._eval_mod11(mod)
        return mod


    def _eval_mod11(self, modulo):
        if modulo == _MODULO_11['BASE']:
            return _MODULO_11['RETORNO11']
        elif modulo == _MODULO_11['BASE'] - 1:
            return _MODULO_11['RETORNO10']
        else:
            return modulo


    @api.multi
    def write(self, vals):
        if not self.manual_sequence and not self.sequence_id:
            vals.update({'name': self.name})
            sequence_id = self._create_sequence(vals).id
            vals.update({'sequence_id': sequence_id}) 
        return super(AccountAuthorization, self).write(vals)
