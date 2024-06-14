# -*- coding: utf-8 -*-

from odoo import api, models
from datetime import datetime

fields = ['credit', 'debit', 'balance']

class ReportFinancial(models.AbstractModel):
    _inherit = 'report.account.report_financial'

    @api.multi
    def encuentra(self, code):
        indice = 0
        while indice < len(code):
            if code[indice] in ['.', '-', ';', ',', '0']:
                return indice + 1
            indice += 1
        return indice

    def _compute_account_balance(self, accounts, report):

        """ compute the balance, debit and credit for the provided accounts
        """
        date_from = datetime.strptime(dict(self._context or {})['date_from'], "%Y-%m-%d")
        open_move = self.env["account.move"].search(
            [("state", "=", "posted"),
             ("date", "=", date_from)])
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
            'is_detail': "True as is_detail",
        }
        acc_first = accounts[0]
        position = self.encuentra(acc_first.code)
        principal_code = acc_first.code[:position]
        q1 = "select id from account_account where id in( " \
             "WITH RECURSIVE nodes(id, parent_id) AS ( " \
             "SELECT s1.id, s1.parent_id FROM account_account s1 WHERE code = %s  " \
             "UNION " \
             "SELECT s2.id, s2.parent_id FROM account_account s2, nodes s1 WHERE s2.parent_id = s1.id and movement = 'account'" \
             ") " \
             "SELECT n.id FROM nodes n) " \
             "order by code"

        self.env.cr.execute(q1, [principal_code])

        accs_temp = self.env.cr.dictfetchall()

        acc_ids = []

        for a in accs_temp:
            acc_ids.append(a["id"])

        res = {}
        for account in accounts:
            res[account.id] = dict((fn, 0.0) for fn in mapping.keys())
        if accounts:
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            request = "SELECT account_id as id, " + ', '.join(mapping.values()) + \
                       " FROM " + tables + \
                       " WHERE account_id IN %s " \
                            + filters + \
                       " GROUP BY account_id"
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row
            if report.beginning_balance:
                if not open_move:
                    query = "SELECT True as is_detail, aml.account_id as id ,COALESCE(SUM(aml.balance),0) as balance, " \
                            "COALESCE(SUM(aml.debit),0) as debit, COALESCE(SUM(aml.credit),0) as credit " \
                            "FROM account_move_line as aml, account_account aa, account_move am " \
                            "WHERE aml.account_id = aa.id " \
                            "AND aml.move_id = am.id " \
                            "AND aa.id IN %s " \
                            "AND aml.date < %s " \
                            "AND am.state = 'posted' " \
                            "GROUP BY aml.account_id " \
                            "ORDER BY aml.account_id asc"
                    self.env.cr.execute(query, (tuple(accounts._ids), dict(self._context or {})['date_from']))
                elif open_move:
                    query = "SELECT True as is_detail, aml.account_id as id ,COALESCE(SUM(aml.balance),0) as balance, " \
                            "COALESCE(SUM(aml.debit),0) as debit, COALESCE(SUM(aml.credit),0) as credit " \
                            "FROM account_move_line as aml, account_account aa, account_move am " \
                            "WHERE aml.account_id = aa.id " \
                            "AND aml.move_id = am.id " \
                            "AND aa.id IN %s " \
                            "AND aml.date >= %s " \
                            "AND aml.date < %s " \
                            "AND am.state = 'posted' " \
                            "GROUP BY aml.account_id " \
                            "ORDER BY aml.account_id asc"
                    params = (tuple(accounts._ids), date_from, dict(self._context or {})['date_from'])
                    self.env.cr.execute(query, params)

                for result in self.env.cr.dictfetchall():
                    if res[result['id']]:
                        saldo_inicial = res[result['id']]['balance'] + result['balance']
                        res[result['id']]['balance'] = saldo_inicial
                        res[result['id']]['is_detail'] = True
                    else:
                        res[result['id']] = result
        if acc_ids:
            for cuenta in acc_ids:
                if report.beginning_balance:
                    qx = "select False as is_detail, %s as id,COALESCE(SUM(aml.balance),0) as balance, " \
                         "COALESCE(SUM(aml.debit),0) as debit, COALESCE(SUM(aml.credit),0) as credit " \
                         "from account_move_line aml, account_move am " \
                         "where aml.account_id in (select id from account_account where id in " \
                         "( WITH RECURSIVE nodes(id, parent_id) AS " \
                         "( SELECT s1.id, s1.parent_id FROM account_account s1 " \
                         "WHERE id in %s " \
                         "UNION SELECT s2.id, s2.parent_id " \
                         "FROM account_account s2, nodes s1 " \
                         "WHERE s2.parent_id = s1.id) " \
                         "SELECT n.id FROM nodes n)) " \
                         "and aml.move_id = am.id " \
                         "and aml.date <= %s " \
                         "and am.state = 'posted' "
                    params = (cuenta,tuple([cuenta]), dict(self._context or {})['date_to'])
                    self.env.cr.execute(qx, params)
                    result_data = self.env.cr.dictfetchall()
                    for row1 in result_data:
                        res[row1['id']] = row1
                else:
                    qx2 = "select False as is_detail, %s as id,COALESCE(SUM(aml.balance),0) as balance, COALESCE(SUM(aml.debit),0) as debit, COALESCE(SUM(aml.credit),0) as credit " \
                         "from account_move_line aml, account_move am " \
                         "where aml.account_id in (select id from account_account where id in " \
                         "( WITH RECURSIVE nodes(id, parent_id) AS " \
                         "( SELECT s1.id, s1.parent_id FROM account_account s1 " \
                         "WHERE id in %s " \
                         "UNION SELECT s2.id, s2.parent_id " \
                         "FROM account_account s2, nodes s1 " \
                         "WHERE s2.parent_id = s1.id) " \
                         "SELECT n.id FROM nodes n)) " \
                         "and aml.move_id = am.id " \
                         "and aml.date >= %s " \
                         "and aml.date <= %s " \
                         "and am.state = 'posted' "
                    params = (cuenta,tuple([cuenta]), dict(self._context or {})['date_from'], dict(self._context or {})['date_to'])
                    self.env.cr.execute(qx2, params)
                    result_data = self.env.cr.dictfetchall() 
                    for row2 in result_data:
                        res[row2['id']] = row2
        return res

    def _compute_report_balance(self, reports):
        '''returns a dictionary with key=the ID of a record and value=the credit, debit and balance amount
           computed for this record. If the record is of type :
               'accounts' : it's the sum of the linked accounts
               'account_type' : it's the sum of leaf accoutns with such an account_type
               'account_report' : it's the amount of the related report
               'sum' : it's the sum of the children of this record (aka a 'view' record)'''
        res = {}
        fields = ['credit', 'debit', 'balance']
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.type == 'accounts':
                # it's the sum of the linked accounts
                res[report.id]['account'] = self._compute_account_balance(report.account_ids, report)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        if value.get('is_detail'):
                            res[report.id][field] += value.get(field)
            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                accounts = self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                res[report.id]['account'] = self._compute_account_balance(accounts, report)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        if value.get('is_detail'):
                            res[report.id][field] += value.get(field)
            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(report.account_report_id)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
            elif report.type == 'sum':
                # it's the sum of the children of this account.report
                res2 = self._compute_report_balance(report.children_ids)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
        return res

    def get_account_lines(self, data):
        lines = []
        account_report = self.env['account.financial.report'].search([('id', '=', data['account_report_id'][0])])
        child_reports = account_report._get_children_by_order()
        res = self.with_context(data.get('used_context'))._compute_report_balance(child_reports)
        if data['enable_filter']:
            comparison_res = self.with_context(data.get('comparison_context'))._compute_report_balance(child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']

        for report in child_reports:
            vals = {
                'name': report.name,
                'balance': res[report.id]['balance'] * report.sign,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type or False, #used to underline the financial report balances
            }
            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * report.sign

            lines.append(vals)
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue

            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance': value['balance'] * report.sign or 0.0,
                        'type': 'account',
                        'level': account.level,
                        'account_type': account.internal_type,
                    }
                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        #if not account.company_id.currency_id.is_zero(vals['debit']) or not account.company_id.currency_id.is_zero(vals['credit']):
                        #    flag = True
                    #if not account.company_id.currency_id.is_zero(vals['balance']):
                    #    flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * report.sign
                        #if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
                        #    flag = True
                    #if flag:
                    sub_lines.append(vals)
                lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])
        return lines

    @api.model
    def get_report_values(self, docids, data=None):
        res = super(ReportFinancial, self).get_report_values(docids, data)
        res['data']['user_name'] = self.env.user.partner_id.name
        new_res = res['data']
        if 'analytic_account_ids' in new_res:
            analytic_ids = self.env['account.analytic.account'].browse(new_res['analytic_account_ids'])
            new_res.update({'analytic_account_ids': ', '.join(x.display_name for x in analytic_ids)})
        return res