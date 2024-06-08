# -*- coding: utf-8 -*-

import re
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    bank_id = fields.Many2one('res.bank', string='Bank', required=True)
    type_account = fields.Selection(selection=[('savings', 'Savings'), ('currents', 'Currents')], string="Type Account", default='savings', required=True)
    cash_number = fields.Char(string='Cash Number', size=100)


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'phone.validation.mixin']

    @api.depends('vat', 'is_validation_vat', 'firstname')
    def _compute_type_vat(self):
        for partner in self:
            vat = partner.vat
            if partner.is_validation_vat or vat:
                vat = re.sub(r'[^A-Z0-9]', '', (vat or '').upper())
                if partner.vat != vat: partner.vat = vat
                partner.type_vat = partner._get_type_vat(partner.vat)
            if partner.type_vat == 'passport':
                partner.vat = vat

    firstname = fields.Char('First name', size=200, track_visibility='always')
    lastname = fields.Char('Last name', size=200, track_visibility='always')
    comercial_name = fields.Char('Cormecial name', size=250, help='Cormecial name')
    is_validation_vat = fields.Boolean('Is validar')
    type_vat = fields.Selection([('vat', 'Vat'),
        ('final_consumer', 'Final consumer'),
        ('ruc', 'RUC (Person natural)'),
        ('ruc_pri', 'RUC (Business private)'),
        ('ruc_pub', 'RUC (Business public)'),
        ('passport', 'Passport'),
        ('invalid', 'Invalid')], readonly=False, compute='_compute_type_vat', store=True, default='invalid')
    l10n_latam_identification_type_id = fields.Many2one('l10n_latam.identification.type',
        string="Identification Type", help="The type of identification")

    def _check_contact(self):
        parent = self
        while parent.parent_id:
            parent = parent.parent_id
        same_vat_partners = self.search(
            [("vat", "=", self.vat.strip()), ("vat", "!=", False), ("company_id", "=", self.company_id.id),
                "|", ("active", "=", True), ("active", "=", False)]
        )
        if same_vat_partners:
            related_partners = self.search(
                [("id", "child_of", parent.id), ("company_id", "=", self.company_id.id),
                    "|", ("active", "=", True), ("active", "=", False)]
            )
            same_vat_partners = self.search(
                [("id", "in", same_vat_partners.ids), ("id", "not in", related_partners.ids), ("company_id", "=", self.company_id.id),
                    "|", ("active", "=", True), ("active", "=", False)]
            )
            if same_vat_partners:
                raise UserError(_("Partner vat must be unique per company except on partner with parent/childe relationship. Partners with same vat and not related, are: %s!")
                    % (", ".join(map(str, same_vat_partners.mapped("name")))))

    
    @api.constrains('vat', 'name')
    def _check_vat_partner(self):
        if self.vat:
            self._check_contact()

    @api.constrains('vat', 'commercial_partner_country_id')
    def check_vat(self):
        if not self.vat == self.vat.strip():
            raise UserError(_('The Identification field contains blank spaces, Please verify that you try to save again.'))
        if self.vat:
            self._check_contact()

    @api.depends('vat', 'firstname', 'lastname')
    def _compute_display_name(self):
        return super(Partner, self)._compute_display_name()

    @api.model
    def create(self, vals):
        company_id = self.env.user.company_id
        if 'vat' in vals:
            type_vat = self._get_type_vat(vals['vat'])
            type_id = self.env['l10n_latam.identification.type'].with_context(active_test=False).search([('ref', '=', type_vat)])
            vals.update({
                'is_validation_vat': True if vals.get('vat', False) else False,
                'l10n_latam_identification_type_id': type_id and type_id.id or False,
                'type_vat': type_vat,
            })
        if 'l10n_latam_identification_type_id' not in vals:
            vals['l10n_latam_identification_type_id'] = self.env.ref('oe_base.it_vat').id
        if 'firstname' not in vals:
            vals['firstname'] = vals.get('name', _('New'))
        if 'lastname' not in vals:
            vals['lastname'] = vals.get('lastname', '')
        if not vals.get('lastname'):
            vals['lastname'] = ''
        if not vals.get('name', False) and vals.get('firstname', False):
            name = '%s %s' % (vals.get('firstname', ''), vals.get('lastname', ''))
            vals['name'] = name
        if vals.get('type', False) == 'delivery':
            vals['customer'] = False
            vals['supplier'] = False
        if 'state_id' not in vals:
            vals['state_id'] = company_id.partner_id.state_id.id
        if 'country_id' not in vals:
            vals['country_id'] = company_id.partner_id.country_id.id
        if 'tz' not in vals:
            vals['tz'] = 'America/Guayaquil'
        return super(Partner, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'vat' in vals:
            type_vat = self._get_type_vat(vals['vat'])
            type_id = self.env['l10n_latam.identification.type'].with_context(active_test=False).search([('ref', '=', type_vat)])
            vals.update({
                'is_validation_vat': True if vals.get('vat', False) else False,
                'type_vat': type_vat,
            })
            if 'l10n_latam_identification_type_id' not in vals and type_id:
                vals.update({'l10n_latam_identification_type_id': type_id.id})
        firstname = self.firstname or ''
        lastname = self.lastname or ''
        if vals.get('firstname', False): firstname = vals.get('firstname', '')
        if vals.get('lastname', False): lastname = vals.get('lastname', '')
        vals['name'] = '%s %s' % (firstname , lastname)
        for partner in self:
            if partner.parent_id and partner.vat:
                if partner.vat == vals.get('vat'):
                    vals['vat'] = False
        return super(Partner, self).write(vals)

    @api.model
    def _commercial_fields(self):
        """ Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. These fields are meant to be hidden on
        partners that aren't `commercial entities` themselves, and will be
        delegated to the parent `commercial entity`. The list is meant to be
        extended by inheriting classes. """
        return ['credit_limit']

    @api.multi
    def name_get(self):
        res = []
        for partner in self:
            if partner.vat and partner.type != 'delivery':
                name = '[%s] %s %s' % (partner.vat or '', partner.firstname or '', partner.lastname or '')
            else:
                name = '%s %s' % (partner.firstname or '', partner.lastname or '')
            
            if self._context.get('show_address_only'):
                name = partner._display_address(without_company=True)
            if self._context.get('show_address'):
                name = name + "\n" + partner._display_address(without_company=True)
            name = name.replace('\n\n', '\n')
            name = name.replace('\n\n', '\n')
            if self._context.get('show_email') and partner.email:
                name = "%s <%s>" % (name, partner.email)
            if self._context.get('html_format'):
                name = name.replace('\n', '<br/>')
            res.append((partner.id, name))
        return res

    @api.onchange('firstname', 'lastname', 'company_type')
    def _onchange_get_name(self):
        res = {}
        if self.company_type == 'company': self.lastname = ''
        if not self.lastname or len(self.lastname):
            self.name = '%s' % self.firstname
        else:
            self.name = '%s %s' % (self.firstname or '', self.lastname or '')
        return res

    @api.model
    def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\t\t\n%(city)s %(state_name)s %(zip)s %(country_name)s"

    @api.multi
    def _display_address(self, without_company=False):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_default_address_format()
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.commercial_company_name or '',
        }
        for field in self._address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

    @api.multi
    def _display_address1(self, without_company=False):
        address_format = "%(street)s\n%(street2)s"
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.commercial_company_name or '',
        }
        for field in self._address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

    @api.multi
    def _display_address2(self, without_company=False):
        address_format = "%(city)s %(state_name)s %(zip)s %(country_name)s"
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.commercial_company_name or '',
        }
        for field in self._address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

    def _split_vat(self, vat):
        return True, True

    def _get_type_vat(self, vat):
        if not vat: 
            return 'invalid'
        if (vat[:2] == 'EC'): vat = vat[2:]
        if vat and vat.isdigit():
            if len(vat) == 13:
                if self._check_consumer(vat): return 'final_consumer'
                elif int(vat[2]) == 9 and self._check_ruc_pri(vat): return 'ruc_pri'
                elif int(vat[2]) == 6 and int(vat[9]) == 0 and self._check_ruc_pub(vat): return 'ruc_pub'
                elif self._check_vat(vat[0:10]): return 'ruc'
            elif len(vat) == 10:
                if self._check_vat(vat): return 'vat'
        return 'passport'

    def _check_ruc_pri(self, vat):
        try:
            state_num = int(vat[0] + vat[1])
            if state_num <= 0 or state_num >= 25:
                return False
            if int(vat[2]) != 9:
                return False
            total = sum([
                int(vat[0]) * 4,
                int(vat[1]) * 3,
                int(vat[2]) * 2,
                int(vat[3]) * 7,
                int(vat[4]) * 6,
                int(vat[5]) * 5,
                int(vat[6]) * 4,
                int(vat[7]) * 3,
                int(vat[8]) * 2
            ])
            veri = total - (int(total / 11)) * 11
            if veri == 0:
                if int(vat[9]) != 0: return False
            else:
                if int(vat[9]) != 11 - veri: return False
            if int(vat[10]) + int(vat[11]) + int(vat[12]) <= 0: return False
            return True
        except:
            return False

    def _check_ruc_pub(self, vat):
        try:
            state_num = int(vat[0] + vat[1])
            if state_num <= 0 or state_num >= 25: return False
            if int(vat[2]) != 6: return False
            total = sum([
                int(vat[0]) * 3,
                int(vat[1]) * 2,
                int(vat[2]) * 7,
                int(vat[3]) * 6,
                int(vat[4]) * 5,
                int(vat[5]) * 4,
                int(vat[6]) * 3,
                int(vat[7]) * 2
            ])
            veri = total - (int(total / 11)) * 11
            if veri == 0:
                if int(vat[8]) != 0: return False
            else:
                if int(vat[8]) != 11 - veri: return False
            if int(vat[9]) + int(vat[10]) + int(vat[11]) + int(vat[12]) <= 0: return False
            return True
        except:
            return False

    def _check_ruc_pnat(self, vat):
        try:
            state_num = int(vat[0] + vat[1])
            if state_num <= 0 or state_num >= 25: return False
            if int(vat[2]) >= 6: return False
            valores = [int(vat[x]) * (2 - x % 2) for x in range(9)]
            suma = sum(map(lambda x: x > 9 and x - 9 or x, valores))
            veri = 10 - (suma - (10 * (int(suma / 10))))
            if int(vat[9]) != int(str(veri)[-1:]): return False
            if int(vat[10]) + int(vat[11]) + int(vat[12]) <= 0: return False
            return True
        except:
            return False

    def _check_vat(self, vat):
        try:
            if vat != '9999999999':
                valores = [int(vat[x]) * (2 - x % 2) for x in range(9)]
                suma = sum(map(lambda x: x > 9 and x - 9 or x, valores))
                veri = 10 - (suma - (10 * int(suma / 10)))
                result = int(vat[9]) == int(str(veri)[-1:])
                return result
            else:
                return False
        except:
            return False

    def _check_consumer(self, vat):
        try:
            return re.sub(r'^\D*', '', vat) == re.sub(r'^\D*', '', self.env.ref('oe_base.final_consumer').vat)
        except:
            return re.sub(r'^\D*', '', vat) in ['9999999999999', 'EC9999999999999']
    
