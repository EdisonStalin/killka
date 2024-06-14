# -*- coding: utf-8 -*-

from odoo import models, tools


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        values = super(MailComposer, self).onchange_template_id(template_id, composition_mode, model, res_id)
        xValue = values['value']
        if model in ['account.invoice', 'account.withholding']:
            doc = self.env[model].browse(res_id)
            if model == 'account.invoice':
                list_ids = []
                if doc.partner_invoice_id: list_ids += [doc.partner_invoice_id.id]
                for x in xValue['partner_ids']:
                    list_ids += x[2]
                    xValue['partner_ids'] = [(6, 0, list_ids)]
        return values

    def _get_attachments(self, values, model=False, res_id=False):
        doc = False
        old_attachment_ids = []
        obj_attachment = self.env['ir.attachment']
        domain = [('res_model', '=', model), ('res_id', '=', res_id)]    
        if model in ['account.invoice', 'account.withholding']:
            doc = self.env[model].browse(res_id)
            if doc and doc.authorization:
                att_pdf = obj_attachment.search(domain + [('datas_fname', '=', '%s.pdf' % doc.authorization_number)], limit=1, order='id desc')
                if att_pdf:
                    for attach_fname, attach_datas in values.get('attachments', []):
                        data_attach = {
                            'name': attach_fname,
                            'datas': attach_datas,
                            'datas_fname': attach_fname,
                            'res_model': model,
                            'res_id': res_id,
                            'type': 'binary',  # override default_type from context, possibly meant for another model!
                        }
                        att_pdf.write(data_attach)
                    old_attachment_ids.append(att_pdf.id)
                    values['attachments'] = []
                att_xml = obj_attachment.search(domain + [('datas_fname', '=', '%s.xml' % doc.authorization_number)], limit=1, order='id desc')
                if att_xml: old_attachment_ids.append(att_xml.id)
        attachment_ids = super(MailComposer, self)._get_attachments(values, model, res_id)
        attachment_ids += old_attachment_ids
        return attachment_ids
