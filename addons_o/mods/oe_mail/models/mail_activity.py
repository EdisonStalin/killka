# -*- coding: utf-8 -*-
from odoo import api, models, fields, SUPERUSER_ID


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    done = fields.Boolean(default=False, help='Activity has been carried out')
    date_done = fields.Datetime(string='Done date', readonly=True, copy=False)
    partner_id = fields.Many2one('res.partner', related='user_id.partner_id', store=True)
    res_model_id_name = fields.Char(
        related='res_model_id.name', string="Origin",
        readonly=True)
    duration = fields.Float(
        related='calendar_event_id.duration', readonly=True)
    calendar_event_id_start = fields.Datetime(
        related='calendar_event_id.start', readonly=True)
    calendar_event_id_partner_ids = fields.Many2many(
        related='calendar_event_id.partner_ids',
        readonly=True)


    @api.multi
    def open_origin(self):
        self.ensure_one()
        vid = self.env[self.res_model].browse(self.res_id).get_formview_id()
        response = {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'view_mode': 'form',
            'res_id': self.res_id,
            'target': 'current',
            'flags': {
                'form': {
                    'action_buttons': False
                }
            },
            'views': [
                (vid, "form")
            ]
        }
        return response

    @api.model
    def action_activities_board(self):
        action = self.env.ref(
            'mail_activity_board.open_boards_activities').read()[0]
        return action

    @api.model
    def _find_allowed_model_wise(self, doc_model, doc_dict):
        doc_ids = list(doc_dict)
        allowed_doc_ids = self.env[doc_model].with_context(
            active_test=False).search([('id', 'in', doc_ids)]).ids
        return set([message_id for allowed_doc_id in allowed_doc_ids
                    for message_id in doc_dict[allowed_doc_id]])

    @api.model
    def _find_allowed_doc_ids(self, model_ids):
        IrModelAccess = self.env['ir.model.access']
        allowed_ids = set()
        for doc_model, doc_dict in model_ids.items():
            if not IrModelAccess.check(doc_model, 'read', False):
                continue
            allowed_ids |= self._find_allowed_model_wise(doc_model, doc_dict)
        return allowed_ids

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        # Rules do not apply to administrator
        if self._uid == SUPERUSER_ID:
            return super(MailActivity, self)._search(
                args, offset=offset, limit=limit, order=order,
                count=count, access_rights_uid=access_rights_uid)

        ids = super(MailActivity, self)._search(
            args, offset=offset, limit=limit, order=order,
            count=False, access_rights_uid=access_rights_uid)
        if not ids and count:
            return 0
        elif not ids:
            return ids

        # check read access rights before checking the actual rules
        super(MailActivity, self.sudo(access_rights_uid or self._uid)).\
            check_access_rights('read')

        model_ids = {}

        self._cr.execute("""
            SELECT DISTINCT a.id, im.id, im.model, a.res_id
            FROM "%s" a
            LEFT JOIN ir_model im ON im.id = a.res_model_id
            WHERE a.id = ANY (%%(ids)s)""" % self._table, dict(ids=ids))
        for a_id, ir_model_id, model, model_id in self._cr.fetchall():
            model_ids.setdefault(model, {}).setdefault(
                model_id, set()).add(a_id)

        allowed_ids = self._find_allowed_doc_ids(model_ids)

        final_ids = allowed_ids

        if count:
            return len(final_ids)
        else:
            # re-construct a list based on ids, because set didn't keep order
            id_list = [a_id for a_id in ids if a_id in final_ids]
            return id_list
