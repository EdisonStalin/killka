# -*- coding: utf-8 -*-

import base64
import io
import logging
import time

from barcode import generate

from odoo import models, api, fields, _
from odoo.exceptions import UserError

from . import utils


_logger = logging.getLogger(__name__)


class AccountWithholding(models.Model):
    _inherit = 'account.withholding'

    edi_document_ids = fields.One2many('account.edi.document', 'withholding_id', 'History')
    batch_id = fields.Many2one('account.edi.document.batch', string='Batch', copy=False)
    
    @api.onchange('authorization', 'received', 'access_key')
    def _onchange_historys(self):
        list_code = []
        res = {'value': {'received': False, 'authorization': False, 'message_state': 'ENVIAR'}}
        codes = self.env['code.validation.document'].search([])
        list_code += [x.code for x in codes]
        for line_id in self.edi_document_ids.filtered(lambda l: l.code not in list_code):
            res['value']['message_state'] = line_id.type
            if line_id.type == 'RECIBIDA':
                res['value']['received'] = True
            if line_id.type == 'AUTORIZADO':
                res['value']['authorization'] = True
        return res

    @api.multi
    def withholding_print(self):
        """ Print the withholding and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.sent = True
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref('oe_edocs.account_withholdings_electronics').report_action(self)

    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        return  self.type == 'out_withholding' and self.state == 'draft' and _('Draft Withholding') or \
                self.type == 'out_withholding' and self.state in ('approved') and not self.authorization and _('Withholding - %s') % (self.number) or \
                self.type == 'out_withholding' and self.state in ('approved') and self.authorization and '%s' % (self.authorization_number)

    def _get_line_specific_history(self, action):
        line = self.env['account.edi.document']
        if len(self.edi_document_ids) > 0:
            domain = [('id', 'in', self.edi_document_ids.ids), ('type', '=', action)]
            line = line.search(domain, limit=1, order='id desc')
        return line

    def _create_fist_history(self):
        if not len(self.edi_document_ids):
            vals = {
                'sequence': 10,
                'code': 0,
                'withholding_id': self.id,
                'type': 'ENVIAR',
                'add_information': self.access_key,
            }
            self.env['account.edi.document'].create(vals)

    def _validate_withholding(self):
        super(AccountWithholding, self)._validate_withholding()
        self.filtered(lambda wh: wh.is_electronic)._create_fist_history()

    @api.multi
    def action_restore_doc(self):
        self.ensure_one()
        self._validate_withholding()

    @api.multi
    def action_send_to_sri(self):
        self.ensure_one()
        cron = self._context.get('cron', False)
        if self.state in ['draft', 'cancel']: return False
        if not self.received:
            self._create_fist_history()
            line_id = self._get_line_specific_history('ENVIAR')
            if line_id:
                line_id._action_send_to_sri(self)
        if self.received and not self.authorization and not cron:
            self.action_validate_to_sri()

    @api.multi
    def action_validate_to_sri(self):
        self.ensure_one()
        if not self.received: return False
        line_id = self._get_line_specific_history('RECIBIDA')
        if line_id:
            line_id._action_validate_to_sri(self)
        if line_id and self.authorization: 
            line_id._action_generate_xml(self)

    def render_document(self):
        vals = {}
        vals.update(utils._info_tributary(self))
        vals.update(self._info_withholding())
        vals.update({'claveAcceso': self.access_key})
        vals.update(self._details_taxes())
        vals.update(self._infoAdicional())
        doc_tmpl = utils._get_type_document(self.type_document_id.code)
        return doc_tmpl.render(vals)

    def _info_withholding(self):
        company = self.company_id
        partner = self.partner_id
        if not partner.l10n_latam_identification_type_id:
            raise UserError(_('The supplier is not validated correctly'))
        
        infoCompRetencion = {
            'fechaEmision': time.strftime('%d/%m/%Y', time.strptime(self.date_withholding, '%Y-%m-%d')),
            'obligadoContabilidad': 'SI' if company.partner_id.check_accounting else 'NO',
            'tipoIdentificacionSujetoRetenido': partner.l10n_latam_identification_type_id.code,
            'razonSocialSujetoRetenido': utils.fix_chars(partner.name),
            'identificacionSujetoRetenido': partner.vat,
            'periodoFiscal': time.strftime('%m/%Y', time.strptime(self.date_withholding, '%Y-%m-%d')),
        }
                     
        establ = self.authorization_id.establishment_id
        if establ:
            dirEstablecimiento = utils.fix_chars(establ._display_address())
            infoCompRetencion.update({'dirEstablecimiento': dirEstablecimiento})
        
        if company.company_registry:
            infoCompRetencion.update({'contribuyenteEspecial': company.company_registry})
        return infoCompRetencion

    def _details_taxes(self):
        impuestos = []
        for line in self.withholding_line_ids:
            date_invoice = line.tmpl_invoice_date or line.invoice_id.date_invoice
            invoice_number = line.tmpl_invoice_number or line.invoice_id.name
            number = invoice_number.split('-')
            tax_id = line.tax_id
            impuesto = {
                'codigo': tax_id.tax_group_id.code,
                'codigoRetencion': tax_id.form_code_ats,
                'baseImponible': '%.2f' % (line.amount_base),
                'porcentajeRetener': abs(tax_id.amount),
                'valorRetenido': '%.2f' % (abs(line.amount)),
                'codDocSustento': line.livelihood_id.code,
                'numDocSustento': ''.join(number),
                'fechaEmisionDocSustento': time.strftime('%d/%m/%Y', time.strptime(date_invoice, '%Y-%m-%d'))
            }
            impuestos.append(impuesto)
        return {'impuestos': impuestos}

    def _infoAdicional(self):
        lines = []
        for line in self.line_info_ids:
            lines.append("""<campoAdicional nombre="%s">%s</campoAdicional>""" % (line.name, line.value_tag))
        infoAdicional = {'infoAdicional': lines}
        return infoAdicional

    @api.multi
    def _get_barcode(self):
        self.ensure_one()
        fp = io.BytesIO()
        generate('code128', self.access_key, output=fp, writer_options={'font_size': 0})
        return base64.b64encode(fp.getvalue())

    @api.multi
    def render_qweb_xml(self, withhold_id):
        domain = [('res_model', '=', self._name), ('res_id', '=', withhold_id.id), ('datas_fname', '=', '%s.xml' % withhold_id.access_key)]
        att_xml = self.env['ir.attachment'].search(domain, limit=1, order='id desc')
        return att_xml

    @api.multi
    def action_generate_xml(self):
        xml_data = self.render_qweb_xml(self)
        if not xml_data:
            line_id = self._get_line_specific_history('AUTORIZADO')
            if not line_id: return False
            line_id._action_generate_xml(self)
        vals = self._onchange_historys()
        self.write(vals['value'])
