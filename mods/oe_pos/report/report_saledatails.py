# -*- coding: utf-8 -*-

import logging
import pytz
from datetime import timedelta
from odoo import models, api, fields, _
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class ReportSaleDetails(models.AbstractModel):

    _inherit = 'report.point_of_sale.report_saledetails'


    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, configs=False):
        """ Serialise the orders of the day information

        params: date_start, date_stop string representing the datetime of order
        """
        if not configs:
            configs = self.env['pos.config'].search([])

        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
        today = today.astimezone(pytz.timezone('UTC'))
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            date_start = today

        if date_stop:
            # set time to 23:59:59
            date_stop = fields.Datetime.from_string(date_stop)
        else:
            # stop by default today 23:59:59
            date_stop = today + timedelta(days=1, seconds=-1)

        # avoid a date_stop smaller than date_start
        date_stop = max(date_stop, date_start)

        date_start = fields.Datetime.to_string(date_start)
        date_stop = fields.Datetime.to_string(date_stop)

        orders = self.env['pos.order'].search([
            ('date_order', '>=', date_start),
            ('date_order', '<=', date_stop),
            ('state', 'in', ['paid','invoiced','done']),
            ('config_id', 'in', configs.ids)])

        user_currency = self.env.user.company_id.currency_id

        t_subtotal = t_cost_subtotal = t_profit = total = 0.0
        products_sold = {}
        taxes = {}
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id.compute(order.amount_total, user_currency)
            else:
                total += order.amount_total
            currency = order.session_id.currency_id

            for line in order.lines:
                key = (line.product_id, line.price_unit, line.discount)
                products_sold.setdefault(key, {
                    'qty': 0.0,
                    'subtotal': 0.0,
                    'cost_subtotal': 0.0,
                    'profit': 0.0})
                products_sold[key]['qty'] += line.qty
                products_sold[key]['subtotal'] += line.price_subtotal
                products_sold[key]['cost_subtotal'] = 0.0
                products_sold[key]['profit'] = 0.0

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount':0.0, 'base_amount':0.0})
                        taxes[tax['id']]['tax_amount'] += tax['amount']
                        taxes[tax['id']]['base_amount'] += tax['base']
                else:
                    taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount':0.0, 'base_amount':0.0})
                    taxes[0]['base_amount'] += line.price_subtotal_incl
        
        for (product, price_unit, discount), values in products_sold.items():
            key = (product, price_unit, discount)
            cost_subtotal = product.standard_price * values['qty']
            profit = products_sold[key]['subtotal'] - cost_subtotal
            t_subtotal += products_sold[key]['subtotal']
            t_cost_subtotal += cost_subtotal
            t_profit += profit
            products_sold[key]['qty'] = '{:.2f}'.format(products_sold[key]['qty'])
            products_sold[key]['subtotal'] = '{:.2f}'.format(products_sold[key]['subtotal'])
            products_sold[key]['cost_subtotal'] = '{:.2f}'.format(cost_subtotal)
            products_sold[key]['profit'] = '{:.2f}'.format(profit)
        
        
        st_line_ids = self.env["account.bank.statement.line"].search([('pos_statement_id', 'in', orders.ids)]).ids
        if st_line_ids:
            self.env.cr.execute("""
                SELECT aj.name, sum(amount) total
                FROM account_bank_statement_line AS absl,
                     account_bank_statement AS abs,
                     account_journal AS aj
                WHERE absl.statement_id = abs.id
                    AND abs.journal_id = aj.id
                    AND absl.id IN %s
                GROUP BY aj.name
            """, (tuple(st_line_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        return {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'subtotal': user_currency.round(t_subtotal),
            'cost_subtotal': user_currency.round(t_cost_subtotal),
            'profit':user_currency.round(t_profit),
            'payments': payments,
            'company_name': self.env.user.company_id.name,
            'taxes': list(taxes.values()),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': values['qty'],
                'subtotal': values['subtotal'],
                'cost_subtotal': values['cost_subtotal'],
                'profit': values['profit'],
                'price_unit': price_unit,
                'discount': discount,
                'uom': product.uom_id.name
            } for (product, price_unit, discount), values in products_sold.items()], key=lambda l: l['product_name'])
        }
