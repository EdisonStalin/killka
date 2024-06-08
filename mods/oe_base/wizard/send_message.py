# -*- coding: utf-8 -*-

from odoo import models, api, fields


class SendMessage(models.TransientModel):
    _name = 'message.wizard'

    user_id = fields.Many2one('res.partner', string='Recipient')
    mobile = fields.Char(related='user_id.mobile', string='Mobile', required=True)
    message = fields.Text(string='Message', required=True)

    @api.onchange('mobile')
    def _onchange_phone_validation(self):
        if self.mobile:
            self.mobile = self.user_id.phone_format(self.mobile)

    @api.multi
    def send_message(self):
        if self.message and self.mobile:
            message_string = ''
            message = self.message.split(' ')
            for msg in message:
                message_string = message_string + msg.replace('\n\n', '%0A%0A') + '%20'
            message_string = message_string[:(len(message_string) - 3)]
            return {
                'type': 'ir.actions.act_url',
                'url': "https://api.whatsapp.com/send?phone=" + self.user_id.mobile + "&text=" + message_string,
                'target': 'self',
                'res_id': self.id,
            }
