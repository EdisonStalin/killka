# -*- coding: utf-8 -*-

from odoo import models, api, fields

class SmsTemplateMessage(models.Model):
    _name = "sms.template.message"
    _description = 'Template Message'


    @api.model
    def default_get(self, fields):
        res = super(SmsTemplateMessage, self).default_get(fields)
        if res.get('model'):
            res['model_id'] = self.env['ir.model']._get(res.pop('model')).id
        return res


    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying the template.")
    name = fields.Char(string='Template', size=200, required=True)
    message = fields.Text('Message', required=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    active = fields.Boolean(default=True, help="Set active to false to hide the template without removing it.")
    model_id = fields.Many2one('ir.model', 'Applies to', help="The type of document this template can be used with")
    model = fields.Char('Related Document Model', related='model_id.model', index=True, store=True, readonly=True)
    