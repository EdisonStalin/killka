# -*- coding: utf-8 -*-

import logging
import os
from subprocess import Popen
import subprocess
import sys
import time

from lxml import etree
from lxml.etree import fromstring, DocumentInvalid
import requests
from requests.exceptions import HTTPError
import zeep

from odoo import _
from odoo.exceptions import UserError


SCHEMAS = {
    '03': '../static/src/schemas/liquidacion_compra_1_1_0.xsd',
    '04': '../static/src/schemas/nota_credito.xsd',
    '05': '../static/src/schemas/nota_debito.xsd',
    '06': '../static/src/schemas/guia_remision.xsd',
    '07': '../static/src/schemas/retencion.xsd',
    '18': '../static/src/schemas/factura_2_1_0.xsd',
}


class SriService(object):
    
    __AMBIENTE_PRUEBA = '1'
    __AMBIENTE_PROD = '2'
    __ACTIVE_ENV = False
    
    __WS_TEST_RECEIV = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
    __WS_TEST_AUTH = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
    __WS_RECEIV = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
    __WS_AUTH = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
    
    __WS_TESTING = (__WS_TEST_RECEIV, __WS_TEST_AUTH)
    __WS_PROD = (__WS_RECEIV, __WS_AUTH)
    
    _WSDL = {
        __AMBIENTE_PRUEBA: __WS_TESTING,
        __AMBIENTE_PROD: __WS_PROD
    }

    @classmethod
    def set_active_env(self, env_service):
        if env_service == self.__AMBIENTE_PRUEBA:
            self.__ACTIVE_ENV = self.__AMBIENTE_PRUEBA
        else:
            self.__ACTIVE_ENV = self.__AMBIENTE_PROD
        self.__WS_ACTIVE = self._WSDL[self.__ACTIVE_ENV]

    @classmethod
    def get_active_env(self):
        return self.__ACTIVE_ENV

    @classmethod
    def get_env_test(self):
        return self.__AMBIENTE_PRUEBA

    @classmethod
    def get_env_prod(self):
        return self.__AMBIENTE_PROD

    @classmethod
    def get_ws_test(self):
        return self.__WS_TEST_RECEIV, self.__WS_TEST_AUTH

    @classmethod
    def get_ws_prod(self):
        return self.__WS_RECEIV, self.__WS_AUTH

    @classmethod
    def get_active_ws(self):
        res = self.__WS_ACTIVE
        return res


class DocumentXML(object):
    _schema = False
    document = False

    @classmethod
    def __init__(self, document=False, code=False, access_key=False, passw=False):
        """
        document: XML representation
        type: determinate schema
        """
        if document:
            parser = etree.XMLParser(ns_clean=True, recover=True, encoding='UTF-8')
            self.document = fromstring(document.encode('UTF-8'), parser=parser)
        self.type_document = code
        self._schema = SCHEMAS[code]
        self.access_key = access_key
        self.passw = passw
        self.logger = logging.getLogger('oe_edocs.models.sri')

    @classmethod
    def _create_xml_unsigned(self, document_xml, path):
        if not os.path.isdir(path):
            os.makedirs(path, mode=0o777)
        path_unsigned = '%s%s' % (path, self.access_key + '.xml')
        # if not os.path.exists(path_unsigned):
        file_signed = open(path_unsigned, 'w')
        file_signed.write(document_xml)
        file_signed.close()

    @classmethod
    def _valid_document_xml(self):
        msg = []
        file_path = os.path.join(os.path.dirname(__file__), self._schema)
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        try:
            xmlschema.assertValid(self.document)
        except DocumentInvalid as err:
            msg += [_('Invalid XML document error: %s') % err]
        return msg
    
    @classmethod
    def _signed_doc_xml(self, dbname, name_p12):
        msg = []
        path = '/tmp/%s/' % dbname
        path_p12 = '%s%s' % (path, name_p12) 
        access_key = self.access_key + '.xml'
        path_signer = '%ssigner/' % path
        if not os.path.isdir(path_signer):
            os.makedirs(path_signer, mode=0o777)
        dir_path = os.path.join(self._moduledir(), 'static', 'src', 'java')
        path_java = os.path.join(dir_path, 'src')
        path_lib = "'.:../lib/*' com/accioma/eris/sign/xades/Signer" if os.name == 'posix'\
            else "%s/lib/*; com.accioma.eris.sign.xades.Signer" % dir_path
        cmd_java = "java -client -Xms64m -Xmx64M -Xss16M -XX:MaxMetaspaceSize=32m "\
            "-XX:CompressedClassSpaceSize=32m -cp %s comprobante %s %s %s %s '%s'"\
            % (path_lib, access_key, path, path_signer, path_p12, self.passw)
        os.chdir(path_java)
        signer_xml = False
        try:
            result = Popen([cmd_java], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            output, errors = result.communicate()
            # self.logger.info(output)
            if errors:
                msg += [errors]
            path = '%s%s' % (path_signer, access_key)
            signer_xml = self.get_exists_signed_xml(path)
        except subprocess.CalledProcessError as e:
            msg += [_('It was not possible to sign the electronic document,\nthe password or the electronic signature is incorrect (%s: %s)') % (e.returncode, e.output)]
        return signer_xml, msg

    @classmethod
    def get_exists_signed_xml(self, path):
        if os.path.exists(path):
            logging.info('Documento firmado')
            file_signed = open(path, 'r')
            document_xml = file_signed.read()
            file_signed.close()
            return document_xml

    @classmethod
    def _moduledir(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(sys.modules[__name__].__file__)))

    @classmethod
    def _check_url_ws(self, url_ws):
        msgs = []
        try:
            transport = zeep.transports.Transport(timeout=7)
            response = requests.get(url_ws)
            if response.status_code != 200:
                content = str(response.content.decode('UTF-8'))
                raise UserError(content)
            client = zeep.Client(wsdl=url_ws, transport=transport)
            return client, msgs
        except ConnectionError as http_err:
            msgs += [_('Connection failed: %s') % http_err]
        except HTTPError as http_err:
            msgs += [_('Connection failed: %s') % http_err]
        except zeep.exceptions.Fault as e:
            msgs += [_('Connection failed: %s') % e.message]
        return False, msgs

    @classmethod
    def send_receipt(self, sent_xml, access_key, sent_type='individual'):
        mistakes = {}
        sent_xml = bytes(sent_xml, 'utf-8')
        url_ws = SriService.get_active_ws()[0]
        try:
            client, msgs = self._check_url_ws(url_ws)
            if client:
                self.logger.info(_('Connection: %s:%s') % (client.service, access_key))
                result = client.service.validarComprobante(sent_xml)
                message_state = result.estado
                self.logger.info(_('Document response status: %s') % message_state)
                if message_state == 'RECIBIDA':
                    mistakes[access_key] = [{
                        'message': '%s en la base del SRI' % message_state,
                        'add_information': access_key,
                        'type': message_state,
                        'date_action': time.strftime("%Y-%m-%d %H:%M:%S"),
                    }]
                    return message_state, mistakes
                else:
                    self.logger.critical(result.comprobantes['comprobante'])
                    for comprobante in result.comprobantes['comprobante']:
                        mistakes.update(self._get_error_message(access_key, comprobante.mensajes))
                    return message_state, mistakes
            else:
                msgs += [_('Unable to establish communication with SRI web service')]
                msg = ',\n'.join(m for m in msgs)
                mistakes[access_key] = [{
                    'code': 70,
                    'message': msg,
                    'add_information': access_key,
                    'type': 'RETRASO',
                    'date_action': time.strftime("%Y-%m-%d %H:%M:%S"),
                }]
                return 'RETRASO', mistakes
        except Exception as ex:
            self.logger.error(_('Connection failed reception: %s') % ex)
            return 'ENVIAR', mistakes

    @classmethod
    def _get_error_message(self, access_key, mensajes):
        mistakes = {}
        list_message = []
        if access_key not in mistakes:
            mistakes[access_key] = []
        for mensaje in mensajes['mensaje']:
            list_message.append({
                'code': int(mensaje.identificador),
                'message': mensaje.mensaje,
                'add_information': mensaje.informacionAdicional,
                'type': mensaje.tipo,
                'date_action': time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        mistakes[access_key] += list_message
        return mistakes

    @classmethod
    def action_request_authorization(self, access_key):
        mistakes = {}
        self.logger.info('Proof consulted: %s' % access_key)
        url_ws = SriService.get_active_ws()[1]
        try:
            client, msgs = self._check_url_ws(url_ws)
            if client:
                self.logger.info(_('Connection: %s') % client.service)
                aresult = client.service.autorizacionComprobante(access_key)
                self.logger.info(_('Number of vouchers %s') % aresult.numeroComprobantes)
                if int(aresult.numeroComprobantes) == 0:
                    return 'RECIBIDA', mistakes
                else:
                    result = aresult.autorizaciones['autorizacion'][0]
                    message_state = result.estado
                    self.logger.info('Authorization status %s' % message_state)
                    if message_state == 'AUTORIZADO':
                        mistakes[self.access_key] = [{
                            'message': {
                                'message_state': message_state,
                                'authorization_number': result.numeroAutorizacion,
                                'authorization_date': str(result.fechaAutorizacion.strftime("%d/%m/%Y %H:%M:%S")),
                                'environment': result.ambiente,
                                'emission_code': '1',
                                'authorization': True,
                            },
                            'add_information': access_key,
                            'type': message_state,
                            'date_action': time.strftime("%Y-%m-%d %H:%M:%S"),
                            'edi_content': result.comprobante,
                        }]
                        return message_state, mistakes
                    else:
                        mistakes.update(self._get_error_message(access_key, result.mensajes))
                    return message_state, mistakes
            else:
                msgs = [_('Unable to establish communication with SRI web service')]
                msg = ',\n'.join(m for m in msgs)
                mistakes[access_key] = [{
                    'code': 70,
                    'message': msg,
                    'add_information': access_key,
                    'type': 'RETRASO',
                    'date_action': time.strftime("%Y-%m-%d %H:%M:%S"),
                }]
                return 'RETRASO', mistakes
        except Exception as ex:
            self.logger.error(_('Connection failed authorization: %s') % ex)
            return 'RECIBIDA', mistakes

