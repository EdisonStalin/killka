# -*- coding: utf-8 -*-

from odoo import models, api, fields, tools


class Establishment(models.Model):
    _name = "res.establishment"
    _description = 'Business Store'
    _order = 'sequence, name'
    
    def _default_company(self):
        return self.env['res.company']._company_default_get('res.partner')

    name = fields.Char(string='Business Store Name', size=100, index=True, required=True)
    sequence = fields.Integer(help='Used to order Companies in the company switcher', default=10)
    code_business = fields.Char(string='Business Store Code', size=3, required=True, default='001', help='Business code that identifies the branches of the others')
    street = fields.Char(string='Street', size=100)
    street2 = fields.Char(string='Street', size=100)
    zip = fields.Char(string='Street', size=10)
    city = fields.Char(string='Street', size=75)
    state_id = fields.Many2one('res.country.state', string="Fed. State")
    country_id = fields.Many2one('res.country', string="Country")
    company_id = fields.Many2one('res.company', 'Company', index=True, default=_default_company)
    email = fields.Char(string='Email', size=250)
    phone = fields.Char(string='Phone', size=50)
    mobile = fields.Char(string='Mobile', size=50)
    website = fields.Char(help="Website of Establishment")
    active = fields.Boolean(default=True)
    comment = fields.Text(string='Notes')
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary("Image", attachment=True,
        help="This field holds the image used as avatar for this contact, limited to 1024x1024px",)
    image_medium = fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized image of this contact. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized image", attachment=True,
        help="Small-sized image of this contact. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    @api.multi
    def _display_address(self):

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
        address_format = "%(street)s\n%(street2)s\n%(city)s %(state_name)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.name or '',
        }
        for field in ['street', 'street2', 'zip', 'city', 'state_id', 'country_id']:
            args[field] = getattr(self, field) or ''
        #address_format = '%(company_name)s\n' + address_format
        return address_format % args

    @api.multi
    def name_get(self):
        res = []
        for estab in self:
            name = estab.name or ''

            if self._context.get('show_address_only'):
                name = estab._display_address()
            if self._context.get('show_address'):
                name = name + "\n" + estab._display_address()
            name = name.replace('\n\n', '\n')
            name = name.replace('\n\n', '\n')
            if self._context.get('show_email') and estab.email:
                name = "%s <%s>" % (name, estab.email)
            if self._context.get('html_format'):
                name = name.replace('\n', '<br/>')
            res.append((estab.id, name))
        return res

    @api.model
    def create(self, vals):
        tools.image_resize_images(vals)
        return super(Establishment, self).create(vals)


    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(Establishment, self).write(vals)
