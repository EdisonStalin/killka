# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class AccountInvoiceConfirm(models.TransientModel):
    _inherit = 'account.invoice.confirm'


    @api.multi
    def invoice_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        invoices = self.env['account.invoice'].search([('id', 'in', active_ids)], order='date_invoice asc')
        for record in self.web_progress_iter(invoices, _('Approve') + "({})".format(self._description)):
            if record.state != 'draft':
                raise UserError(_("Selected invoice(s) cannot be confirmed as they are not in 'Draft' state."))
            record.action_invoice_open()
        return {'type': 'ir.actions.act_window_close'}
