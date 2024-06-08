# -*- coding: utf-8 -*-

from odoo import models, api, exceptions
from odoo.tools.misc import split_every


class Message(models.Model):

    _inherit = 'mail.message'


    @api.model
    def _get_reply_to(self, values):
        """ Return a specific reply_to: alias of the document through
        message_get_reply_to or take the email_from """
        model, res_id, email_from = values.get('model', self._context.get('default_model')), values.get('res_id', self._context.get('default_res_id')), values.get('email_from')  # ctx values / defualt_get res ?
        if model and hasattr(self.env[model], 'message_get_reply_to'):
            company_id = self.env.user.company_id
            string_reply_to = '%s <%s>' % (company_id.name or '', company_id.email or '')
            return string_reply_to
        else:
            # return self.env['mail.thread'].message_get_reply_to(default=email_from)[None]
            return self.env['mail.thread'].message_get_reply_to([None], default=email_from)[None]


class Partner(models.Model):
    _inherit = 'res.partner'


    """@api.model
    def _notify_send(self, body, subject, recipients, **mail_values):
        emails = self.env['mail.mail']
        recipients_nbr = len(recipients)
        partners_sudo = self.sudo().env['res.partner']
        for email_chunk in split_every(50, recipients.ids):
            # TDE FIXME: missing message parameter. So we will find mail_message_id
            # in the mail_values and browse it. It should already be in the
            # cache so should not impact performances.
            mail_message_id = mail_values.get('mail_message_id')
            message = self.env['mail.message'].browse(mail_message_id) if mail_message_id else None
            if message and message.model and message.res_id and message.model in self.env and hasattr(self.env[message.model], 'message_get_recipient_values'):
                tig = self.env[message.model].browse(message.res_id)
                recipient_values = tig.message_get_recipient_values(notif_message=message, recipient_ids=email_chunk)
                followers = self.sudo().env['mail.followers'].search([
                    ('res_model', '=', tig._name),
                    ('res_id', '=', tig.id),
                    ('partner_id', 'not in', self.ids),
                ])
                partners_sudo |= followers.mapped('partner_id')
            else:
                recipient_values = self.env['mail.thread'].message_get_recipient_values(notif_message=None, recipient_ids=email_chunk)
            create_values = {
                'body_html': body,
                'subject': subject,
            }
            create_values.update(mail_values)
            create_values.update(recipient_values)
            if len(partners_sudo) > 0:
                create_values.update({'email_cc': ','.join([x.email for x in partners_sudo])})
            emails |= self.env['mail.mail'].create(create_values)
        return emails, recipients_nbr"""
        