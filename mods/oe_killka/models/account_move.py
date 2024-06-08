# -*- coding: utf-8 -*-

import logging

from odoo import models, api, _

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'


    @api.multi
    def assert_balanced(self):
        if not self.ids:
            return True
        prec = self.env['decimal.precision'].precision_get('Account')
        self._cr.execute("""\
            SELECT move_id, abs(sum(debit) - sum(credit)) AS amount, 
                sum(debit) AS sum_debit, sum(credit) AS sum_credit
            FROM        account_move_line
            WHERE       move_id in %s
            GROUP BY    move_id
            HAVING      abs(sum(debit) - sum(credit)) > %s
            """, (tuple(self.ids), 10 ** (-max(3, prec))))
        result = self._cr.fetchall()
        if len(result) != 0:
            for line in result:
                msg = _("Cannot create unbalanced journal entry. %s: amount %s Debit: %s Credit: %s") % (self.narration, line[1], line[2], line[3])
                _logger.critical(msg)
                #raise UserError(msg)
        return True
