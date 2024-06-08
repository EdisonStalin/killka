# -*- coding: utf-8 -*-

import base64

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError
from odoo.http import content_disposition
from odoo.http import request


class PortalAccount(CustomerPortal):
    
    # ------------------------------------------------------------
    # My Invoices
    # ------------------------------------------------------------
    
    @http.route(['/my/invoices/pdf/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_report(self, invoice_id, access_token=None, **kw):
        try:
            invoice_sudo = self._invoice_check_access(invoice_id, access_token)
        except AccessError:
            return request.redirect('/my')

        # print report as sudo, since it require access to taxes, payment term, ... and portal
        # does not have those access rights.
        pdf = request.env.ref('account.account_invoices').sudo().render_qweb_pdf([invoice_sudo.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', content_disposition(invoice_sudo.authorization_number + '.pdf')),
        ]
        response = request.make_response(pdf, headers=pdfhttpheaders)
        response.set_cookie('fileToken', access_token)
        return response

    @http.route(['/my/invoices/xml/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_report_xml(self, invoice_id, access_token=None, **kw):
        try:
            invoice_sudo = self._invoice_check_access(invoice_id, access_token)
        except AccessError:
            return request.redirect('/my')

        # print report as sudo, since it require access to taxes, payment term, ... and portal
        # does not have those access rights.
        xml = request.env['account.invoice'].sudo().render_qweb_xml(invoice_sudo)
        data = base64.b64decode(xml.datas)
        xmlhttpheaders = [
            ('Content-Type', 'application/xml'),
            ('Content-Length', xml.file_size),
            ('Content-Disposition', content_disposition(xml.name)),
        ]
        response = request.make_response(data, headers=xmlhttpheaders)
        response.set_cookie('fileToken', access_token)
        return response

