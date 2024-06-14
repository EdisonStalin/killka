# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PrintPreNumberedChecks(models.TransientModel):
    _inherit = 'print.prenumbered.checks'

    next_check_number = fields.Char('Next Check Number', required=True)

    @api.multi
    def print_checks(self):
        check_number = self.next_check_number
        payments = self.env['account.payment'].browse(self.env.context['payment_ids'])
        payments.filtered(lambda r: r.state == 'draft').post()
        payments.filtered(lambda r: r.state not in ('sent', 'cancelled')).write({'state': 'sent'})
        for payment in payments:
            payment.check_number = check_number
        return payments.do_print_checks()
