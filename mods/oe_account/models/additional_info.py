# -*- coding: utf-8 -*-

from odoo import models, fields


class InfoAdditional(models.Model):
    _name = "additional.info"
    _description = "Additional Information"
    _order = "sequence,id"


    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the invoice.")
    invoice_id = fields.Many2one('account.invoice', string='Invoice Reference',
        ondelete='cascade', index=True)
    withholding_id = fields.Many2one('account.withholding', string='Withholding Reference',
        ondelete='cascade', index=True)
    authorization_id = fields.Many2one('account.authorization', string='Withholding Reference',
        ondelete='cascade', index=True)
    name = fields.Char(string='Reference', size=150, required=True, help='Additional information reference')
    value_tag = fields.Char(string="Detail", size=250, required=True, help="Value of the additional información reference")

