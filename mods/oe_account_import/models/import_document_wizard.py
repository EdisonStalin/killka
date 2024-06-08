# -*- coding: utf-8 -*-

import base64
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ImportDocumentWizard(models.TransientModel):
    _name = "import.document.wizard"
    _description = "Import Document Wizard"
    
    #('create', 'Create'),
    type = fields.Selection(selection=[('import', 'Import')], default='import')
    file = fields.Binary(string="Import File")
    datas_fname = fields.Char('Import File Name')


    @api.multi
    def action_document_import(self):
        purchase_id = False
        if self._context.get('default_purchase_id', False):
            purchase_id = self.env['purchase.order'].browse(self._context.get('default_purchase_id'))
        xml_data = base64.decodestring(self.file)
        vals = {
            'file': xml_data,
            'file_name': self.datas_fname or purchase_id.name,
            'file_type': 'text/xml',
            'res_model': 'account.invoice',
            'type_document': 'in_invoice',
        }
        base_import_id = self.env['base_import.import'].create(vals)
        vals, error = base_import_id._get_review_xml(xml_data)
        if len(error):
            _logger.error(','.join(error))
            raise UserError(','.join(error))
        invoice_line_ids=vals['invoice_line_ids']
        del vals['invoice_line_ids']
        vals.update({'purchase_id': purchase_id.id})
        invoice_id = self.env['account.invoice'].with_context(
            default_purchase_id=purchase_id.id,
            invoice_line_ids=invoice_line_ids).create(vals)
        invoice_id.purchase_order_change()
        invoice_id._onchange_invoice_line_ids()
        invoice_id._compute_amount()
        return purchase_id.action_view_invoice()
        
    

