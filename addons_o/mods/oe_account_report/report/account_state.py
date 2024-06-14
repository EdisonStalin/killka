# -*- coding: utf-8 -*-

from odoo import tools
from odoo import api, models, _
from odoo.exceptions import UserError


LIST_OUT = ['out_invoice', 'out_refund', 'in_withholding', 'inbound']
LIST_IN = ['in_invoice', 'in_refund', 'out_withholding', 'outbound']

class ReportAccountState(models.AbstractModel):
    _name = 'report.oe_account_report.report_account_state'

    
    def _select_invoice(self):
        sql = """
            SELECT 1 AS "order", i.id, i.partner_id as partner, t.name as "document", i.type AS "type", i.name as "name", 
            COALESCE(i.origin, '') AS origin, i.date_invoice AS date, 
            (i.amount_total - i.amount_withhold) AS total, 0.0 AS balance,
            i.id AS main_doc
            FROM account_invoice i
            LEFT JOIN account_type_document t ON (t.id=i.type_document_id)
            WHERE i.state IN ('open','paid')
        """
        return sql


    def _select_withhold(self):
        sql = """
            SELECT 2 AS "order", w.id, w.partner_id AS partner, 'Retención' AS "document",
            w.type AS "type", w.name AS "name", COALESCE(wl.tmpl_invoice_number, w.origin) AS origin,
            w.date_withholding AS date, SUM(-wl.amount) AS total, 0.0 AS balance,
            wl.invoice_id AS main_doc
            FROM account_withholding_line wl
            LEFT JOIN account_withholding w on (w.id=wl.withholding_id)
            LEFT JOIN account_type_document t ON (t.id=w.type_document_id)
            WHERE w.state IN ('approved')
            GROUP by w.id, w.partner_id, w.type, w.name, wl.tmpl_invoice_number, w.origin, w.date_withholding, wl.invoice_id
        """
        return sql


    def _select_payment(self):
        sql = """
            SELECT 3 AS "order", p.id, p.partner_id AS partner, 'Pago' AS "document", 
            p.payment_type AS "type", p.name AS "name", COALESCE(p.communication, '') AS origin, 
            p.payment_date AS date, p.amount AS total, 0.0 AS balance,
            pi.invoice_id AS main_doc
            FROM account_payment p
            JOIN account_invoice_payment_rel pi ON (pi.payment_id=p.id)
            WHERE p.state IN ('posted','sent','reconciled')
        """
        return sql

    
    def _generate_report_view(self):
        sql = self._select_invoice() + """
            UNION
            """ + self._select_withhold() + """
            UNION
            """ + self._select_payment()
        return sql
    
    
    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'history_account_state')
        sql = """CREATE OR REPLACE VIEW history_account_state AS ("""+ self._generate_report_view() +""" ORDER BY date ASC)""" 
        self.env.cr.execute(sql)


    def _get_lines(self, data):
        obj_invoice = self.env['account.invoice']
        domain = [('id', 'in', data['partner_ids'])] if len(data['partner_ids']) else []
        partner_ids = self.env['res.partner'].search(domain, order="name asc")
        move_lines = []
        lines = {x.id: {'vat': x.vat or '', 'name': x.name, 'total': 0.0, 'lines': []} for x in partner_ids}
        cr = self.env.cr
        if data.get('type_partner') == 'customer': list_type = LIST_OUT 
        if data.get('type_partner') in ['supplier', 'employee']: list_type = LIST_IN
        sql = """SELECT * FROM history_account_state 
            WHERE partner IN %s AND type IN %s AND date <= %s
            ORDER BY main_doc,"order" ASC,date ASC;"""
        params = (tuple(partner_ids.ids,), tuple(list_type), data['date_to'])
        cr.execute(sql, params)
        for row in cr.dictfetchall():
            if row['type'] in ['outbound', 'inbound']:
                invoice_id = obj_invoice.browse(row['main_doc'])
                for vals in invoice_id._get_payments_vals():
                    if vals.get('account_payment_id') and vals['account_payment_id'] == row['id']:
                        row['total'] = vals['amount']
            if row['type'] in ['outbound', 'inbound', 'out_refund', 'in_refund']:
                row['total'] = -row['total']
            row['residual'] = 0.0
            if row['order'] == 1:
                invoice_id = obj_invoice.browse(row['main_doc'])
                row['residual'] = invoice_id.residual
            lines[row.pop('partner')]['lines'].append(row)
        for key in lines:
            total_residual = 0.0
            if len(lines[key]['lines']) > 0:
                for line in lines[key]['lines']:
                    total_residual += line['residual']
                    line['balance'] += line['total']
                lines[key]['total'] = total_residual
                move_lines.append(lines[key])
        return move_lines
        


    @api.model
    def get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        lines = self._get_lines(data['form'])
        return {
            'data': data['form'],
            'move_lines': lines,
        }

