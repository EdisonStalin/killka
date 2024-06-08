# -*- coding: utf-8 -*-

import logging

from odoo import models, _

_logger = logging.getLogger(__name__)

class ReportBankStatement(models.AbstractModel):
    _name = "report.oe_account.bank_statement"
    _inherit = "report.report_xlsx.abstract"
    _description = "Bank Statement Report xlsx"

    def _get_report_columns(self):
        res = {
            0: {'header': _('Date'), 'field': 'date', 'type': 'string', 'width': 15},
            1: {'header': _('Description'), 'field': 'name', 'type': 'string', 'width': 25},
            2: {'header': _('Ref'), 'field': 'ref', 'type': 'string', 'width': 25},
            3: {'header': _('Amount'), 'field': 'amount', 'type': 'amount', 'width': 15},
        }
        return res

    def _build_content(self, object_id):
        for line_object in object_id:
            result = self.write_line(line_object)
            #_logger.info(_('Result: %s') % result)
        _logger.info(_('Generation of successfully generated lines'))

    def generate_xlsx_report(self, workbook, data, objects):
        self.row_pos = 0
        self._define_formats(workbook)
        self.sheet = workbook.add_worksheet(_('Bank Statement'))
        
        # Columns Creation on employee
        self.columns = self._get_report_columns()
        for object_id in objects.mapped('line_ids'):
            self._set_column_width()
            self.write_array_header()
            self._build_content(object_id)

