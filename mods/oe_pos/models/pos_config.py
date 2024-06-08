# -*- coding: utf-8 -*-

import logging

from odoo import models, api, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _name = 'pos.config'
    _inherit = ['pos.config', 'mail.thread', 'mail.activity.mixin']

    
    def session_payment(self):
        for res in self:
            details = []
            bg_colore = [ '', 'cadetblue', 'rosybrown', 'rosyblue', 'coral', 'darkcyan', 'lightcoral', 'cornflowerblue', 'cadetblue', 'rosybrown', 'rosyblue', 'coral', 'darkcyan', 'lightcoral', 'cornflowerblue' ]
            total = 0
            for session in res.session_ids:
                payment_id = self.env['account.bank.statement'].search([('name', '=', session.name)])
                for each in payment_id:
                    session_id = self.env['pos.session'].search([('name', '=', each.name)])
                    if session_id.state == 'opened':
                        details.append({'payment':each.journal_id.name_get()[0][1],
                                        'amount':each.total_entry_encoding,
                                        'currency':each.currency_id.symbol})
                        total += each.total_entry_encoding
            body = """<table  style='width: 100%;'>"""
            count = 0
            for data in details:
                count += 1
                size = (data['amount'] * 100) / total  if data['amount'] else 0
                body += """<tr>"""
                body += """<td style="text-align:left;width: 40%;/* font-size: 16px; */color: blue;">""" + data['payment'] + """</td>"""
                body += """<td style="text-align:left; width: 70%;">
               <div class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"
                    style="width:""" + '100' + """%;background-color:white;border-radius:10px;height:16px; -moz-border-radius: 3px;-webkit-border-radius:
                                10px;border:1px solid #f0eeef;">
                    <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"
                    style="width:""" + format(size, '.0f') + """%;background-color:""" + bg_colore[count] + """;height:14px;border-radius:10px; -moz-border-radius: 3px;-webkit-border-radius:
                                10px;line-height: 14px;font-size: 10px;color:black;">""" + format(size, '.0f') + '%' + """
                                </div>
                </div>
                </td>
               """
                body += """<td style="text-align:left;color:  firebrick;width: 20%;"><div style='margin-left: 5px;'>""" + data['currency'] + str(data['amount']) + """</div></td>"""
                body += """</tr>"""
            body += "</table>"
            res.payment_details = body


    def session_total_count(self):
        session_list = self.env['pos.session'].search([('state','=','opened')])
        for sessions in session_list:
            for each1 in sessions.config_id:
                    each1.total_sesstion = len(sessions)
                    each1.total_details_count = """
                                <table style="height: 24px;" width="100%">
                                <tbody>
                                    <tr>
                                        <td style="width: 55%;">Subtotal sin IVA:</td>
                                        <td style="width: 40%;">
                                            <div class="progress mb0" style="height: 15px;width:100%" >
                                                  
                                                    <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"
                                                        style="width:""" + format((each1.untaxamount_total * 100) / each1.subtotal_session  if each1.untaxamount_total else 0, '.0f') + """%;background-color:rosybrown;">
                                                        <span style="font-size:0px;display:  initial;">""" + str(each1.untaxamount_total) + """</span> 
                                                          
                                                    </div>
                                            </div>
                                        </td>
                                        <td style="width: 5%;margin-bottom: 3px;">""" + str(round(each1.untaxamount_total,2)) + """</td>
                                    </tr>
                                    <tr>
                                        <td style="width: 55%;margin-top: 10px;">Total IVA:</td>
                                        <td style="width: 40%;margin-top: 10px;">
                                            <div class="progress mb0" style="height: 15px;width:100%" >
                                                  
                                                    <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"
                                                        style="width:""" + format((each1.tax_amount * 100) / each1.subtotal_session  if each1.tax_amount else 0, '.0f') + """%;background-color:limegreen;">
                                                       <span style="font-size:0px;display:  initial;"> """ + str(each1.tax_amount) + """</span> 
                                                    </div>
                                            </div>
                                        </td>
                                        <td style="width: 5%;margin-bottom: 3px;">""" + str(round(each1.tax_amount,2)) + """</td>
                                    </tr>
                                    <tr>
                                        <td style="width: 55%;margin-top: 10px;">Total:</td>
                                        <td style="width: 40%;margin-top: 10px;">
                                            <div class="progress mb0" style="height: 15px;width:100%" >
                                                    <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"
                                                        style="width: """ + format((each1.subtotal_session * 100) / each1.subtotal_session  if each1.subtotal_session else 0, '.0f') + """%;">
                                                         <span style="font-size:0px;display:  initial;"> """ + str(each1.subtotal_session) + """</span> 
                                                    </div>
                                            </div>
                                        </td>
                                         <td style="width: 5%;margin-bottom: 3px;">""" + str(round(each1.subtotal_session,2)) + """</td>
                                    </tr>
                                </tbody>
                            </table>
                  
                        """


    image = fields.Binary(string='Image', help='Image to be shown on ticket and POS')
    default_partner_id = fields.Many2one('res.partner', string="Select Customer", 
                                         required=True, domain="[('customer','=',True)]")
    establishment_id = fields.Many2one('res.establishment', string='Business Store', track_visibility='always')
    authorization_id = fields.Many2one('account.authorization', string='Authorization', required=True, track_visibility='always')
    refund_authorization_id = fields.Many2one('account.authorization', string='Refund Authorization', track_visibility='always')
    check_refund = fields.Boolean(string='Check Refund', track_visibility='always', help='Allow order return')
    # Stock
    location_only = fields.Boolean(string='Only in POS Location', default=True)
    hide_product = fields.Boolean(string='Hide Products not in POS Location', default=True)
    
    untaxamount_total = fields.Float('Subtotal', related='session_ids.untaxamount_total',digits=(16,2))
    tax_amount = fields.Float('Total VAT', related='session_ids.tax_amount',digits=(16,2))
    subtotal_session = fields.Float('Total', related='session_ids.subtotal_session',digits=(16,2))
    number_of_order = fields.Integer('Total Order', related='session_ids.number_of_order')
    total_discount = fields.Float('Total discount(%)', related='session_ids.total_discount')
    sale_qty = fields.Integer('Total Qty Sale', related='session_ids.sale_qty')
    total_done_order = fields.Integer('Total Done Order', related='session_ids.total_done_order')
    total_cancel_order = fields.Integer('Total Cancel Order', related='session_ids.total_cancel_order')
    payment_details_ids = fields.One2many('account.bank.statement', 'pos_session_id', string='Payments', relared='session_ids.statement_ids' , store=True, readonly=True)
    payment_details = fields.Html('Payment Details', compute='session_payment')
    payment_graph = fields.Html('Payment Graph', compute='session_payment')
    total_details_count = fields.Html('Total Details', compute='session_total_count')
    total_sesstion = fields.Integer('Total', compute='session_total_count')
    
    pos_lock = fields.Boolean(string='Enable Lock Screen')
    bg_color = fields.Char('Background Color', default='rgb(218, 218, 218)',
                           help='The background color of the lock screen, (must be specified in a html-compatible format)')
    lock_price = fields.Boolean(string='Lock price', default=False)
    lock_discount = fields.Boolean(string='Lock discount', default=False)
    lock_password = fields.Char(string='Password', size=50)
    allow_service = fields.Boolean(string='Allow Service Charges')
    service_category_id = fields.Many2one('pos.category', string='Service Charges Category')

    
    @api.constrains('lock_password')
    def check_price_password(self):
        if self.lock_price is True or self.lock_discount is True:
            for item in str(self.lock_password):
                try:
                    int(item)
                except Exception as e:
                    _logger.error(e)
                    raise ValidationError(_("The unlock price password should be a number"))


    @api.model
    def default_get(self, fields):
        vals = super(PosConfig, self).default_get(fields)
        if 'default_partner_id' not in vals:
            vals['default_partner_id'] = self.env.ref('oe_base.final_consumer').id
        return vals


    @api.multi
    def get_action_pos_order(self):
        return {
                'name': _('Pos order'),
                'type': 'ir.actions.act_window',
                'res_model': 'pos.order',
                'view_mode': 'tree',
                'view_type': 'form',
                'domain': [('session_id', '=', self.session_ids.id)],
            }
    


class PosStockChannel(models.TransientModel):
    _name = 'pos.stock.channel'

    def broadcast(self, stock_quant):
        data = stock_quant.read(['product_id', 'location_id', 'quantity'])
        self.env['bus.bus'].sendone((self._cr.dbname, 'pos.stock.channel'), data)
