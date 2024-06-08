# -*- coding: utf-8 -*-

import xlwt
import io
import base64
from datetime import datetime
from odoo import tools
from odoo import models, api, _
from . import excel_styles as xs

class AccountBalanceReport(models.TransientModel):
    _inherit = 'account.balance.report'


    @api.multi
    def check_report_excel(self):
        res = super(AccountBalanceReport, self).check_report()
        return self._print_report_excel(res)


    @api.multi
    def _print_report_excel(self, data):
        workbook = xlwt.Workbook()

        financial_report_obj = self.env['report.account.report_trialbalance']
        get_account_lines = financial_report_obj.with_context(active_model='account.balance.report',
                                                              active_ids=self.ids).get_report_values(None, data=data['data'])

        sheet_name = _('Trial Balance')
        sheet = workbook.add_sheet(sheet_name)
        comp_id = self.env.user.company_id
        #sheet.write_merge(Fila posicion Y, Fila Ancho hacia Abajo, Celda Posición X, Celda Ancho a Derecha, Texto, Estilo)
        sheet.write_merge(0, 1, 0, 3, self._description, xs.subTitle_style)
        sheet.write_merge(2, 2, 0, 1, comp_id.name, xs.normal_style_text)
        sheet.write_merge(2, 2, 2, 3, _('Printing Date: %s') % datetime.now().strftime('%Y-%m-%d'), xs.normal_style_text)
        
        
        if self.date_from:
            sheet.write(3, 2, _('Date from:'), xs.normal_style_left)
            sheet.write(4, 2, self.date_from, xs.normal_style_text_left_sub)
        if self.date_to:
            sheet.write(3, 3, _('Date To:'), xs.normal_style_left)
            sheet.write(4, 3, self.date_to, xs.normal_style_text_left_sub)
        
        sheet.write(3, 0, _('Target Moves:'), xs.normal_style_left)
        if self.target_move == 'all':
            sheet.col(0).width = 256 * 15
            sheet.col(1).width = 256 * 50
            sheet.col(2).width = 256 * 18
            sheet.col(3).width = 256 * 18
            sheet.col(4).width = 256 * 18
            sheet.write(3, 1, _('All Entries'),xs.normal_style_text_left_sub)

        if self.target_move == 'posted':
            sheet.col(0).width = 256 * 15
            sheet.col(1).width = 256 * 50
            sheet.col(2).width = 256 * 18
            sheet.col(3).width = 256 * 18
            column = sheet.col(8)
            column.width = 256 * 18
            sheet.write(3, 1, _('All Posted Entries'), xs.normal_style_text_left_sub)
        

        sheet.write(6, 0, _('code'), xs.subTitle_style_color)
        sheet.write(6, 1, _('Name'), xs.subTitle_style_color)
        sheet.write(6, 2, _('Debit'), xs.subTitle_style_color)
        sheet.write(6, 3, _('Credit'), xs.subTitle_style_color)
        sheet.write(6, 4, _('Balance'), xs.subTitle_style_color)

        row_data = 7
        for line in get_account_lines.get('Accounts', []):
            sheet.write(row_data, 0, tools.ustr(line['code']), xs.normal_style_left)
            sheet.write(row_data, 1, tools.ustr(line['name']), xs.normal_style_left)
            sheet.write(row_data, 2, tools.ustr(line['debit']), xs.normal_style_num)
            sheet.write(row_data, 3, tools.ustr(line['credit']), xs.normal_style_num)
            sheet.write(row_data, 4, tools.ustr(line['balance']), xs.normal_style_num)
            row_data+=1
        
        row_data+=3
        sheet.write(row_data, 1, _('Makes:'), xs.normal_style_left_bottom)
        row_data+=3
        sheet.write(row_data, 1, _('Approve:'), xs.normal_style_left_bottom)
        row_data+=3
        sheet.write(row_data, 1, _('Receives:'), xs.normal_style_left_bottom)
        
        
        stream = io.BytesIO()
        workbook.save(stream)
        attach_id = self.env['accounting.finance.report.output.wizard'].create({'name': '%s.xls' % self._description, 'xls_output': base64.encodestring(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'accounting.finance.report.output.wizard',
            'res_id':attach_id.id,
            'type': 'ir.actions.act_window',
            'target':'new'
        }
