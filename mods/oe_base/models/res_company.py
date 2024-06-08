# -*- coding: utf-8 -*-

import base64
import os
import sys

from odoo import models, api, fields
from odoo.exceptions import UserError


class Company(models.Model):
    _inherit = 'res.company'

    def _moduledir(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(sys.modules[__name__].__file__)))

    def _get_logo_login(self):
        path = self._moduledir()
        return base64.b64encode(open(os.path.join(path, 'static', 'src', 'img', 'logo_login.png'), 'rb') .read())

    @api.one
    @api.depends('company_favicon')
    def _get_favicon(self):
        if self.company_favicon:
            self.favicon_url = 'data:image/png;base64,' + str(self.company_favicon.decode('UTF-8'))

    @api.one
    @api.depends('logo_login')
    def _get_company_logo(self):
        if self.logo_login:
            self.logo_login_url = 'data:image/png;base64,' + str(self.logo_login.decode('UTF-8'))

    code_business = fields.Char(string='Code Business', size=3, required=True, default='001', help='Business code that identifies the branches of the others')
    comercial_name = fields.Char('Cormecial name', size=250, help='Cormecial name')
    establishments_ids = fields.One2many('res.establishment', 'company_id', string='Business Store', domain=[('active', '=', True)])
    dashboard_background = fields.Binary(string='Background', attachment=True, help="This field holds the image used as avatar for this contact, limited to 1600x900px",)
    logo_login = fields.Binary(string='Image Login', default=_get_logo_login, attachment=True, help="This field holds the image used as avatar for this contact, limited to 1600x1024px",)
    logo_report = fields.Binary(string='Image Report', default=_get_logo_login, attachment=True, help="This field holds the image used as report for this contact, limited to 1024x1024px",)
    logo_signed = fields.Binary(string='Image Signed', default=_get_logo_login, attachment=True, help="This field holds the image used as signed for this contact, limited to 1024x1024px",)
    company_favicon = fields.Binary(string='Favicon', default=_get_logo_login, attachment=True, help="This field holds the image used for as favicon")
    name_software = fields.Char(string='Name Software', size=50, default='App EcuaOnline', help='Program name who developed the software')
    web_software = fields.Char(string='Website', size=150, default='https://www.appecuaonline.net', help='Website the company in charge of developing the software')
    favicon_url = fields.Char(string='Url', compute='_get_favicon')
    logo_login_url = fields.Char(string='Url', compute='_get_company_logo')
    documentation_url = fields.Char(string='Documentation Url', size=250, default='#')
    support_url = fields.Char(string='Support Url', size=250, default='#')
    account_url = fields.Char(string='My Odoo.com Account Url', size=250, default='#')
    email_edoc = fields.Char(string='Sender Mail', copy=False, help='Email that who is being sent')
    smtp_pass = fields.Char(string='Password', help="Optional password for SMTP authentication")

    @api.constrains('name', 'comercial_name', 'vat')
    def _check_get_name(self):
        if self.vat:
            partners = self.search([('vat', '=', self.vat), ('id', '!=', self.id)])
            if len(partners) >= 1:
                raise UserError(_('%s to create already exists in the system, check in the client or supplier of the Sales and Purchases tab, enable the configurations') % (', '.join(['%s - %s' % (par.name, par.vat) for par in partners])))

    @api.multi
    def _get_logo_report(self, establishment=False):
        logo = self.logo
        if self.logo_report and not establishment:
            logo = self.logo_report
        if establishment and establishment.image:
            logo = establishment.image
        if 'logo_report' in self._context and self._context.get('logo_report', False):
            ids = self._context.get('active_ids', [])
            values = self.env[self._context.get('active_model')].browse(ids).read([self._context.get('field', '')])[0]
            logo = values.get(self._context.get('field', ''))
        return logo
