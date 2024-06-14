# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class L10nLatamIdentificationType(models.Model):
    _name = 'l10n_latam.identification.type'
    _description = "Identification Types"
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    name = fields.Char(translate=True, required=True,)
    description = fields.Char()
    active = fields.Boolean(default=True)
    is_vat = fields.Boolean()
    country_id = fields.Many2one('res.country')
    code = fields.Char(string='Document Code', required=True, size=2)
    ref = fields.Char(string='Reference', size=25)

    def name_get(self):
        result = []
        for rec in self:
            name = rec.name
            if rec.code:
                name = '(%s) %s' % (rec.code, name)
            result.append((rec.id, name))
        return result
