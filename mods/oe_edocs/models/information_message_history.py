# -*- coding: utf-8 -*-

import os
import time
import logging

from odoo import models, api, fields, _

from odoo.exceptions import UserError
from jinja2 import Environment, FileSystemLoader

from . import utils
from .sri import SriService, DocumentXML

_logger = logging.getLogger(__name__)

class InformationMessageHistory(models.Model):
    _name = "information.message.history"
    _description = "History Information Message SRI"
    _order = 'sequence desc, id desc'
    
    @api.model
    def _get_company(self):
        return self.env.user.company_id
    
    sequence = fields.Integer(help='Used to order Companies in the company switcher', default=10)
    code = fields.Integer(string='Code', help='Result code of the SRI')
    message = fields.Char(string='Message', size=250, help='Message info')
    add_information = fields.Text(string='Additional information', help='Additional information')
    type = fields.Char(string='Type', size=50, help='Information type')
    date_action = fields.Datetime(string="Action", default=fields.Datetime.now,)
    validation_id = fields.Many2one('code.validation.document', string='Validation', help='Relation validation')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', help='Relation invoice')
    withholding_id = fields.Many2one('account.withholding', string='Withholding', help='Relation invoice')
    transport_id = fields.Many2one('transport.permit', string='Transport Permit', help='Relation Transport')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=_get_company,
        help='The company this user is currently working for.')

    
    @api.model
    def create(self, vals):
        if 'validation_id' not in vals and 'code' in vals:
            domain = [('code', '=', vals['code'])]
            code = self.env['code.validation.document'].search(domain)
            if code: vals['validation_id'] = code.id
        return super(InformationMessageHistory, self).create(vals)


    def _generate_key_access(self, document_id):
        if 'withholding' == document_id._name:
            date_document = document_id.date_withholding
        elif 'transport' == document_id._name:
            date_document = document_id.date_transport
        else:
            date_document = document_id.date_invoice
        if document_id.is_electronic and document_id.type_document_id.code_doc_xml and (not\
            document_id.access_key and not document_id.received or not document_id.authorization):
            access_key = document_id.authorization_id.generation_access_key(document_id.name, document_id.type_document_id, date_document)
        else:
            access_key = document_id.access_key
        return access_key


    def _get_code(self, document_id):
        code = 0
        if len(document_id.history_ids):
            first_history = self._get_first_history().validation_id.type_action
            code = self._get_first_history().code
        if code in [43]: self._action_validate_to_sri()
        if not document_id.received and first_history == 'send':
            access_key = self._generate_key_access(document_id)
            _logger.info('Create access key: %s' % access_key)
            document_id.write({'access_key': access_key, 'message_state':'SIN FIRMAR'})
            document_id._cr.commit()


    def _generation_xml(self, access_key, document_id):
        mistakes = {}
        errors = []
        cron = self._context.get('cron', False)
        doc_xml = document_id.render_document()
        password, name_p12 = self.company_id._generation_signed()
        message_state = 'FIRMADO'
        if password and name_p12:
            code = document_id.type_document_id.code
            path = '/tmp/%s/' % self._cr.dbname
            DocumentXML.__init__(doc_xml, code, access_key, password)
            msg = DocumentXML._valid_document_xml()
            errors += msg
            DocumentXML._create_xml_unsigned(doc_xml, path)
            doc_xml, msg = DocumentXML._signed_doc_xml(self._cr.dbname, name_p12)
            errors += msg
        else:
            errors += [_('Unable to sign the password or the certificate is encountering problems')]
            message_state = 'NO FIRMADO'
            mistakes[access_key] = [{
                'message': ',\n'.join(errors),
                'message': message_state,
                'add_information': access_key,
                'type': 'ERROR',
                'date_action': time.strftime("%Y-%m-%d %H:%M:%S"),
            }]
        if len(errors):
            msg = _('Signature %s') % ',\n'.join(errors)
            _logger.error(msg)
            if cron:
                raise UserError(msg)
        else:
            _logger.info(_('Signature %s') % message_state)
        return [doc_xml], message_state, mistakes


    def _create_history(self, mistakes, document_id):
        vals = {}
        if 'withholding' == document_id._name:
            document = 'withholding_id'
        elif 'transport' == document_id._name:
            document = 'transport_id'
        else:
            document = 'invoice_id'
        if document_id.access_key in mistakes:
            for line in mistakes[document_id.access_key]:
                _logger.info(line['message'])
                line[document] = document_id.id
                if line['type'] == 'RECIBIDA':
                    line_id = document_id._get_line_specific_history('ENVIAR')
                    line_id.write(line)
                    return vals
                if line['type'] == 'AUTORIZADO':
                    vals.update(line['message'])
                self.create(line)
        return vals


    def _check_web_service(self):
        env = self.company_id.environment
        if not utils.chek_reception(env):
            raise UserError(_('SRI: at the moment the SRi services are not available or are under maintenance'))
        SriService.set_active_env('1' if env == 'test' else '2')


    def _action_send_to_sri(self, document_id):
        cron = document_id._context.get('cron', False)
        self._check_web_service()
        if len(document_id.history_ids) > 2:
            msg = _("""You have exceeded the number of attempts allowed per day 3 in the SRI.\n
                Check the incidents that have occurred in the SRI Information. %s of %s""") % (document_id.type_document_id.name, document_id.name)
            _logger.info(msg)
            if not cron: raise UserError(msg)
        if len(document_id.history_ids) < 2:
            access_key = document_id.access_key
            if not access_key:
                access_key = self._generate_key_access(document_id)
                document_id.access_key = access_key
            if document_id.access_key:
                doc_xml, message_state, mistakes = self._generation_xml(access_key, document_id)
                if len(doc_xml) == 1:
                    message_state, mistakes = DocumentXML.send_receipt(doc_xml[0], access_key)
                else:
                    message_state, mistakes = DocumentXML.send_receipt(doc_xml, access_key, 'lote')
                vals = {
                    'received': True if message_state == 'RECIBIDA' else False,
                    'message_state': message_state,
                    'access_key': access_key,
                }
                vals.update(self._create_history(mistakes, document_id))
                document_id.write(vals)
            document_id._cr.commit()


    def _create_document_xml(self, auth_edocument, document_id):
        if auth_edocument: _logger.info(_('The XML document was created in the system'))
        if not auth_edocument: _logger.debug(_('The XML document is not created in the system'))
        list_attachment = [('%s.xml' % document_id.access_key, auth_edocument)]
        message = """
        CLAVE DE ACCESO: %s <br>
        NÚMERO DE AUTORIZACIÓN %s <br>
        FECHA AUTORIZACIÓN: %s <br>
        ESTADO DE AUTORIZACIÓN: %s <br>
        AMBIENTE: %s <br>
        """ % (
            document_id.access_key,
            document_id.authorization_number,
            document_id.authorization_date,
            document_id.message_state,
            document_id.environment,
        )
        document_id.message_post(body=message, attachments=list_attachment)


    def _action_generate_xml(self, document_id):
        xml_data = document_id.render_qweb_xml(document_id)
        if not xml_data:
            xml_data = document_id.render_document()
            tmpl_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'src', 'templates')
            env = Environment(loader=FileSystemLoader(tmpl_path))
            auth_xml = {
                'estado': document_id.message_state,
                'numeroAutorizacion': document_id.authorization_number,
                'fechaAutorizacion': document_id.authorization_date,
                'ambiente': document_id.environment,
                'comprobante': xml_data
            }
            edocument_tmpl = env.get_template('authorized_document.xml')
            xml_data = edocument_tmpl.render(auth_xml)
            self._create_document_xml(xml_data, document_id)


    def _action_validate_to_sri(self, document_id):
        cron = document_id._context.get('cron', False)
        self._check_web_service()
        if len(document_id.history_ids) > 2:
            msg = _("""You have exceeded the number of attempts allowed per day 3 in the SRI.\n
                Check the incidents that have occurred in the SRI Information. %s of %s""") % (document_id.type_document_id.name, document_id.name)
            _logger.critical(msg)
            if not cron: raise UserError(msg)
        DocumentXML.__init__(False, document_id.type_document_id.code, document_id.access_key, False)
        message_state, mistakes = DocumentXML.action_request_authorization(document_id.access_key)
        vals = {
            'authorization': True if message_state == 'AUTORIZADO' else False,
            'message_state': message_state
        }
        vals.update(self._create_history(mistakes, document_id))
        document_id.write(vals)
        document_id._cr.commit()
        if document_id.authorization:
            self._action_generate_xml(document_id)


class InfoAdditional(models.Model):
    _inherit= 'additional.info'
    
    transport_id = fields.Many2one('transport.permit', string='Transport Reference', ondelete='cascade', index=True)
    
