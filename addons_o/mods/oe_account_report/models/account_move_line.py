# Copyright 2019 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).-
from odoo import api, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.multi
    def total_debit_credit(self):
        res = {}
        for move in self:
            dr_total = 0.0
            cr_total = 0.0
            for line in move._get_move_lines():
                dr_total += line.debit
                cr_total += line.credit
            res.update({'dr_total': dr_total, 'cr_total': cr_total})
        return res
    
    @api.multi
    def _get_move_withholds(self):
        invoice_id = self.line_ids.mapped('invoice_id')
        withhold_ids = invoice_id.withholding_id.filtered(lambda w: w.state=='approved')
        return withhold_ids
            
    @api.multi
    def _get_invoice(self):
        return self.line_ids.mapped('invoice_id')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_cr
    def init(self):
        """
            The join between accounts_partners subquery and account_move_line
            can be heavy to compute on big databases.
            Join sample:
                JOIN
                    account_move_line ml
                        ON ap.account_id = ml.account_id
                        AND ml.date < '2018-12-30'
                        AND ap.partner_id = ml.partner_id
                        AND ap.include_initial_balance = TRUE
            By adding the following index, performances are strongly increased.
        :return:
        """
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = '
                         '%s',
                         ('account_move_line_account_id_partner_id_index',))
        if not self._cr.fetchone():
            self._cr.execute("""
            CREATE INDEX account_move_line_account_id_partner_id_index
            ON account_move_line (account_id, partner_id)""")
