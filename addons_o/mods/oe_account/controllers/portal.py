# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq


class PortalAccount(CustomerPortal):
    
    def _prepare_portal_layout_values(self):
        values = super(PortalAccount, self)._prepare_portal_layout_values()
        values.update({
            'error': {},
            'error_message': [],
            'vat': '',
        })
        return values

    # ------------------------------------------------------------
    # My Withholding
    # ------------------------------------------------------------

    def _withholding_check_access(self, withholding_id, access_token=None):
        withholding = request.env['account.withholding'].browse([withholding_id])
        withholding_sudo = withholding.sudo()
        try:
            withholding.check_access_rights('read')
            withholding.check_access_rule('read')
        except AccessError:
            if not access_token or not consteq(withholding_sudo.access_token, access_token):
                raise
        return withholding_sudo


    def _withholding_get_page_view_values(self, withholding, access_token, **kwargs):
        values = {
            'page_name': 'withholding',
            'withholding': withholding,
        }
        if access_token:
            values['no_breadcrumbs'] = True
            values['access_token'] = access_token

        if kwargs.get('error'):
            values['error'] = kwargs['error']
        if kwargs.get('warning'):
            values['warning'] = kwargs['warning']
        if kwargs.get('success'):
            values['success'] = kwargs['success']

        return values

    @http.route(['/my/withholdings/<int:withholding_id>'], type='http', auth="public", website=True)
    def portal_my_withholding_detail(self, withholding_id, access_token=None, **kw):
        try:
            withholding_sudo = self._withholding_check_access(withholding_id, access_token)
        except AccessError:
            return request.redirect('/my')

        values = self._withholding_get_page_view_values(withholding_sudo, access_token, **kw)
        return request.render("oe_account.portal_withholding_page", values)

