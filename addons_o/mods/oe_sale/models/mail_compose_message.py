# -*- coding: utf-8 -*-

from odoo import models

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'


    """def onchange_template_id(self, template_id, composition_mode, model, res_id):
        values = super(MailComposer, self).onchange_template_id(template_id, composition_mode, model, res_id)
        att_ids = []
        if 'attachment_ids' in values['value']:
            for value in values['value']['attachment_ids']:
                att_ids += value[2]
        if model in ['sale.order']:
            sale = self.env[model].browse(res_id)
            for line in sale.order_line:
                domain = [('res_model', '=', 'product.template'), ('res_field', '=', 'sheet_product_id'), ('res_id', '=', line.product_id.id)]
                att = self.env['ir.attachment'].search(domain)
                if att:
                    att.write({'name': line.product_id.filename_product, 'datas_fname': line.product_id.filename_product})
                    att_ids.append(att.id)
            if len(att_ids): values['value']['attachment_ids'] = [(6, 0, att_ids)]
        return values"""

