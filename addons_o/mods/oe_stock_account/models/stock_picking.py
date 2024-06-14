# -*- coding: utf-8 -*-

from odoo import models, api


class Picking(models.Model):
    _inherit = 'stock.picking'


    @api.multi
    def action_get_account_moves(self):
        self.ensure_one()
        action_ref = self.env.ref('account.action_move_journal_line')
        if not action_ref:
            return False
        action_data = action_ref.read()[0]
        account_move_ids = []
        for line in self.move_lines:
            account_move_ids += line.account_move_ids.ids
        action_data['domain'] = [('id', 'in', account_move_ids)]
        return action_data
