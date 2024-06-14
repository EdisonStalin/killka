# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError


class SendSMS(models.TransientModel):
    _inherit = 'sms.send_sms'
    
    tmpl_message_id = fields.Many2one('sms.template.message', string='Message Template', help='The template of message to be sent will be applied.')
    model = fields.Char(string='Related Document Model', required=True)


    @api.model
    def default_get(self,default_fields):
        res = super(SendSMS, self).default_get(default_fields)
        if 'model' not in res:
            res['model'] = self._context.get('active_model')
        return res
    

    @api.onchange('tmpl_message_id')
    def _onchange_tmpl_message_id(self):
        if self.tmpl_message_id:
            self.message = self.tmpl_message_id.message


    def _send_whatsapp(self, mobile, sms_message):
        return {
            'type': 'ir.actions.act_url',
            'url': "https://api.whatsapp.com/send?phone="+mobile+"&text=" + sms_message,
            'target': 'new',
            'res_id': self.id,
        }
    
    
    def _sms_message(self, sms_message):
        message_string = ''
        for msg in sms_message.split(' '):
            message_string = message_string + msg.replace('\n\n', '%0A%0A') + '%20'
        message_string = message_string[:(len(message_string) - 3)]
        return message_string


    def _action_send_whatsapp(self, sms_message, numbers=None, partners=None):
        """ Send an SMS text message and post an internal note in the chatter if successfull
            :param sms_message: plaintext message to send by sms
            :param partners: the numbers to send to, if none are given it will take those
                                from partners or _get_default_sms_recipients
            :param partners: the recipients partners, if none are given it will take those
                                from _get_default_sms_recipients, this argument
                                is ignored if numbers is defined
            :param note_msg: message to log in the chatter, if none is given a default one
                             containing the sms_message is logged
        """
        if not numbers:
            if not partners:
                partners = self._get_default_sms_recipients()

            # Collect numbers, we will consider the message to be sent if at least one number can be found
            numbers = list(set([i.mobile for i in partners if i.mobile]))

        if numbers:
            for mobile in numbers:
                message = self._sms_message(sms_message)
                action = self._send_whatsapp(mobile, message)
        else:
            UserError(_('You do not have mobile numbers entered to send the message.'))
            
        records = self.env[self._context['active_model']].browse(self._context['active_ids'])
        for thread in records:
            thread.message_post(body=sms_message)
        return action


    @api.multi
    def action_send_whatsapp(self):
        user = self.env.user
        numbers = [number.strip() for number in self.recipients.split(',') if number.strip()]
        if not user.mobile:
            raise UserError(_('You have not entered the mobile of user %s.') % user.name)
        return self._action_send_whatsapp(self.message, numbers)
