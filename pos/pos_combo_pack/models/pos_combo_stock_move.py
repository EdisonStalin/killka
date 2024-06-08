# -*- coding: utf-8 -*-
# See README file for full copyright and licensing details.
from odoo import api, models
from functools import partial

class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = "pos.order"
    _description = "Point of Sale"
    _order = "id desc"

    def _order_fields(self,ui_order):
        
       
        
        process_line = partial(self.env['pos.order.line']._order_line_fields, session_id=ui_order['pos_session_id'])
        order_lines = [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False
        new_order_line = []
        for order_line in order_lines:
            new_order_line.append(order_line)
            if order_line[2].get('combo_ids'):
                x_order = order_line[2]
                combo_pro_list = list()
                if x_order['combo_ids']:
                    for l in x_order['combo_ids']:
                        combo_pro_list += [process_line(l)]
                else:
                    combo_pro_list = False
                if combo_pro_list:
                    for combo in combo_pro_list:
                        new_order_line.append(combo)
            if order_line[2].get('own_ids'):
                own_pro_list = [process_line(l) for l in order_line[2]['own_ids']] if order_line[2]['own_ids'] else False
                if own_pro_list:
                    for own in own_pro_list:
                        new_order_line.append(own)


        return {
            'name':         ui_order['name'],
            'user_id':      ui_order['user_id'] or False,
            'session_id':   ui_order['pos_session_id'],
            'lines':        new_order_line,
            'pos_reference':ui_order['name'],
            'partner_id':   ui_order['partner_id'] or False,
            'date_order':   ui_order['creation_date'],
            'fiscal_position_id': ui_order['fiscal_position_id'],
            'pricelist_id': ui_order['pricelist_id'],
        }