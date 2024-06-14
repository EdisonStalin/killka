# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.fields import Field, Float, Selection
from odoo.tools import html_escape as escape

from ..models.decimal_precision import DecimalPrecision as dp


def convert_to_export(self, value, record):
    import_data = record._context.get('import_compat', False)
    if not isinstance(self.selection, list) or import_data:
        return value if value else ''
    for item in self._description_selection(record.env):
        if item[0] == value:
            return item[1]
    return False


Selection.convert_to_export = convert_to_export

native_get_description = Field.get_description


def new_get_description(self, env):
    desc = native_get_description(self, env)
    if getattr(self, '_digits', None) and callable(self._digits) and \
            self._digits.__closure__:
        application = self._digits.__closure__[0].cell_contents
        desc['digits'] = dp.get_display_precision(env, application)
    return desc


Field.get_description = new_get_description


def get_digits(self, env):
    if isinstance(self.digits, str):
        precision = env['decimal.precision'].precision_get(self.digits)
        return 16, precision
    else:
        return 16, 2

    
Float.get_digits = get_digits


class Establishment(models.AbstractModel):
    _name = 'ir.qweb.field.establishment'
    _inherit = 'ir.qweb.field.many2one'
    
    @api.model
    def value_to_html(self, value, options):
        if not value.exists():
            return False

        opf = options and options.get('fields') or ["address", "phone", "mobile", "email"]
        value = value.sudo().with_context(show_address=True)
        name_get = value.name_get()[0][1]

        val = {
            'address': escape("\n".join(name_get.split("\n")[1:])).strip(),
            'phone': value.phone,
            'mobile': value.mobile,
            'city': value.city,
            'country_id': value.country_id.display_name,
            'website': value.website,
            'email': value.email,
            'fields': opf,
            'object': value,
            'options': options
        }
        return self.env['ir.qweb'].render('oe_base.establishment', val, **options.get('template_options'))

    def get_digits(self, env):
        if isinstance(self._digits, str):
            precision = env['decimal.precision'].precision_get(self._digits)
            return 16, precision
        else:
            return self._digits
