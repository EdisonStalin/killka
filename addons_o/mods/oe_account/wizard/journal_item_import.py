# -*- coding:utf-8 -*-

import base64
from datetime import datetime

import xlrd

from odoo import models, fields, api, _
from odoo import tools
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class JournalItem(models.TransientModel):
    _name = 'journal.item.wizard'
    
    files = fields.Binary(string="Import Excel File")
    datas_fname = fields.Char('Import File Name')
    
    @api.multi
    def journal_item(self):
        for rec in self:
            rec._item_import()
    
    @api.model
    def _item_import(self):
        active_id = self._context.get('active_id')
        item_lines = []
        partner_obj = self.env['res.partner']
        accountmove_obj = self.env['account.move'].browse(active_id)
        accountmove_line_obj = self.env['account.move.line']
        account_obj = self.env['account.account']
        analytic_obj = self.env['account.analytic.account']
        currency_obj = self.env['res.currency']
        try:
            workbook = xlrd.open_workbook(file_contents=base64.decodestring(self.files))
        except:
            raise ValidationError(_('Please select .xls/xlsx file...'))
        Sheet_name = workbook.sheet_names()
        sheet = workbook.sheet_by_name(Sheet_name[0])
        number_of_rows = sheet.nrows
        row = 1
        while(row < number_of_rows):
            codev = tools.ustr(sheet.cell(row,0).value)
            account_id = account_obj.search([('code', '=', codev), ('company_id', '=', accountmove_obj.company_id.id)])
            if not account_id:
                raise ValidationError(_('Account Code %s is not found at row number %s') % (sheet.cell(row,0).value,row))
            partner_id = partner_obj.search(['|', '|', ('vat','=',sheet.cell(row,1).value), ('name', 'ilike', sheet.cell(row,1).value), ('display_name', 'ilike', sheet.cell(row,1).value),
                                             ('company_id', '=', accountmove_obj.company_id.id)], order='id ASC', limit=1)
            analytic_id = analytic_obj.search([('name', '=', sheet.cell(row,3).value)])
            #if not analytic_id:
                #raise ValidationError('Analytic Account %s is not found at row number %s '%(sheet.cell(row,0).value,row))
            cur = tools.ustr(sheet.cell(row,5).value)
            currency_id = currency_obj.search([('name', '=', cur)])
            if not sheet.cell(row,0).value:
                raise ValidationError(_('%s Account Code should not be empty at row number %s') % (sheet.cell(row,0).value,row))
            if not sheet.cell(row,2).value:
                raise ValidationError(_('%s Label should not be empty at row number %s') % (sheet.cell(row,2).value,row))
            #if not sheet.cell(row,8).value:
                #raise ValidationError('%s DUE DATE should not be empty at row number %s '%(sheet.cell(row,8).value,row))
            create_date = sheet.cell(row,10).value
            date_maturity = sheet.cell(row,8).value
            create_date = datetime.strptime(create_date, "%d/%m/%Y").strftime(DF)
            date_maturity = datetime.strptime(date_maturity, "%d/%m/%Y").strftime(DF)
            vals = {
                'account_id' : account_id.id,
                'partner_id' : partner_id and partner_id.id or False,
                'name' : sheet.cell(row,2).value,
                'analytic_account_id' : analytic_id.id,
                'amount_currency' : sheet.cell(row,4).value,
                'currency_id' : currency_id.id,
                'debit' : sheet.cell(row,6).value,
                'credit' : sheet.cell(row,7).value,
                'date_maturity': date_maturity,
                'ref' : sheet.cell(row, 9).value,
                'date' : create_date,
                'move_id': active_id,
                }
            item_lines.append((0, 0, vals))
            row = row+1
        accountmove_obj.write({'line_ids' : item_lines})
        return True
