# -*- coding: utf-8 -*-

from odoo import models, api


class ReportTax(models.AbstractModel):
    _inherit = 'report.account.report_tax'
    
    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".tax_line_id||'-'||tm.account_account_tag_id AS id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                    FROM %s
                    JOIN account_account_tag_account_move_line_rel tm ON (tm.account_move_line_id=account_move_line.id)
                    WHERE %s AND "account_move_line".tax_exigible
                    GROUP BY "account_move_line".tax_line_id, tm.account_account_tag_id"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT "account_move_line".tax_line_id||'-'||tm.account_account_tag_id AS id, COALESCE(SUM("account_move_line".tax_base_amount), 0)
                 FROM %s
                 JOIN account_account_tag_account_move_line_rel tm ON (tm.account_move_line_id=account_move_line.id)
                 WHERE %s AND "account_move_line".tax_exigible
                 GROUP BY "account_move_line".tax_line_id, tm.account_account_tag_id"""
        return sql

    def _action_get_lines(self, options):
        domain = [('date_invoice','>=',options['date_from']), ('date_invoice','<=',options['date_to'])]
        invoice_ids = self.env['account.invoice'].search(domain)
        for invoice in invoice_ids:
            tax_tag_ids = self.env['account.account.tag']
            for line in invoice.invoice_line_ids:
                tax_tag_ids = line.tax_tag_ids
                tax_tag_ids |= line.invoice_line_tax_ids.mapped('tag_ids').filtered(lambda l: l.document_type in invoice.type)
                line.write({'tax_tag_ids': [(6, 0, tax_tag_ids.ids)]})
            for line in invoice.move_id.mapped('line_ids').filtered(lambda l: l.tax_line_id):
                line.write({'tax_tag_ids': [(6, 0, tax_tag_ids.ids)]})
            tax_grouped = invoice.get_taxes_values()
            if len(tax_grouped): invoice._refresh_lines_taxes(tax_grouped)
        
        domain = [('date_withholding','>=',options['date_from']), ('date_withholding','<=',options['date_to'])]
        withhold_ids = self.env['account.withholding'].search(domain)
        for withhold in withhold_ids:
            tax_tag_ids = self.env['account.account.tag']
            for line in withhold.withholding_line_ids:
                tax_tag_ids = line.tax_tag_ids
                tax_tag_ids |= line.tax_id.mapped('tag_ids').filtered(lambda l: l.document_type in withhold.type)
                line.write({'tax_tag_ids': [(6, 0, tax_tag_ids.ids)]})
            for line in withhold.move_id.mapped('line_ids').filtered(lambda l: l.tax_line_id):
                line.write({'tax_tag_ids': [(6, 0, tax_tag_ids.ids)]})
    
    @api.model
    def get_lines(self, options):
        taxes = {}
        self._action_get_lines(options)
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            for tag in tax.tag_ids:
                if tax.children_tax_ids:
                    for child in tax.children_tax_ids:
                        if child.type_tax_use != 'none':
                            continue
                        key = '%s-%s' % (str(child.id), tag.id)
                        taxes[key] = {'tax': 0, 'net': 0, 'locker': tag.name, 'name': child.name, 'type': tax.type_tax_use, 'code': child.account_id.code, 'account': child.account_id.name, 'qty': 0}
                else:
                    key = '%s-%s' % (str(tax.id), tag.id)
                    taxes[key] = {'tax': 0, 'net': 0, 'locker': tag.name, 'name': tax.name, 'type': tax.type_tax_use, 'code': tax.account_id.code, 'account': tax.account_id.name, 'qty': 0}

        self.with_context(date_from=options['date_from'], date_to=options['date_to'], strict_range=True)._compute_from_amls(options, taxes)
        groups = dict((tp, []) for tp in ['sale', 'purchase', 'all'])
        for tax in taxes.values():
            groups[tax['type']].append(tax)
        return groups
