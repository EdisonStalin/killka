# -*- coding: utf-8 -*-


from odoo import http
from odoo.addons.base_import import controllers


class ImportController(http.Controller):

    @http.route('/base_import/set_file', methods=['POST'])
    def set_file(self, file, import_id, jsonp='callback'):
        doc_file = self.env['base_import.import'].browse(int(import_id))
        if doc_file.res_model == 'account.invoice':
            res = self.env[doc_file.res_model]
        return super(ImportController, self).set_file(file, import_id, jsonp)