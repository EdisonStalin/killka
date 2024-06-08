# -*- coding: utf-8 -*-

import base64
import logging

from odoo import api, models
from odoo.tools.mimetypes import guess_mimetype
from datetime import datetime

_logger = logging.getLogger(__name__)

class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'
    
    @api.multi
    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()
        # Check raw data
        currency_id = self.env.user.company_id.currency_id
        vals = {
            'res_model': 'account.bank.statement',
            'file': base64.b64decode(self.data_file),
            'file_name': self.filename,
            'file_type': guess_mimetype(self.data_file),
        }
        file_import = self.env['base_import.import'].with_context(active_id=self.ids[0]).create(vals)
        result = file_import.parse_preview({}, count=100)
        file_name = self.filename.lower()
        if file_name.strip().endswith('.xlsx') and 'preview' in result:
            statement = False
            vals_list = []
            for line in result['preview'][1:]:
                values = {
                    'date': line[2],
                    'name': line[3],
                    'ref': len(line[4]) and line[4] or line[3],
                    'amount': line[7],
                    'currency_id': currency_id.id,
                    'journal_id': self.env.context.get('active_id'),
                }
                vals_list.append((0, 0, values))
            values = {
                'name': 'Statement Of ' + str(datetime.today().date()),
                'journal_id': self.env.context.get('active_id'),
                'line_ids': vals_list
            }
            if len(vals_list) != 0:
                statement = self.env['account.bank.statement'].create(values)
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.bank.statement',
                    'view_mode': 'form',
                    'res_id': statement.id,
                    'views': [(False, 'form')],
                }
    