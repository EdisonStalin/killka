# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError


class AccountInvoiceSent(models.TransientModel):
    """
    This wizard will sent the all the selected draft invoices
    """

    _name = "account.invoice.sent"
    _description = "Sent the selected invoices"

    @api.multi
    def invoice_confirm_sent(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        invoices = self.env['account.invoice'].browse(active_ids)
        if invoices.filtered(lambda inv: inv.state not in ['open', 'paid']):
            raise UserError(_("The invoice must be open to send to the SRI"))
        if invoices.filtered(lambda inv: inv.authorization == True):
            raise UserError(_("The invoice must not be authorized by the SRI"))
        for invoice in self.web_progress_iter(invoices, _('Sending to SRI') + "({})".format(self._description)):
            invoice.action_send_to_sri()
        return {'type': 'ir.actions.act_window_close'}


class AccountWithholdingSent(models.TransientModel):
    """
    This wizard will sent the all the selected draft withholdings
    """

    _name = "account.withholding.sent"
    _description = "Sent the selected withholdings"

    @api.multi
    def withholding_confirm_sent(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['account.withholding'].browse(active_ids):
            if record.state == 'draft':
                raise UserError(_("Selected withholding(s) cannot be sent SRI as they are in %s 'Draft' state.") % record.partner_id.name)
            record.action_send_to_sri()
        return {'type': 'ir.actions.act_window_close'}
    

class TransportPermitSent(models.TransientModel):
    """
    This wizard will sent the all the selected draft transport permit
    """

    _name = "transport.permit.sent"
    _description = "Sent the selected transport permit"

    @api.multi
    def transport_confirm_sent(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['transport.permit'].browse(active_ids):
            if record.state == 'draft':
                raise UserError(_("Selected transport permit(s) cannot be sent SRI as they are in %s 'Draft' state.") % record.partner_id.name)
            record.action_send_to_sri()
        return {'type': 'ir.actions.act_window_close'}

