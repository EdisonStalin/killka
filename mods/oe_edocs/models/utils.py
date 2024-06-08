# -*- coding: utf-8 -*-

import os
import sys
import time

from jinja2 import Environment, FileSystemLoader
import requests

codeTax = {
    '0': '0',
    '12': '2',
    '14': '3',
    'novat': '6',
    'excento': '7'
}

TEMPLATES = {
    '03': 'out_settlement_v1.1.0.xml',
    '04': 'out_refund_credit_v1.1.0.xml',
    '05': 'out_refund_debit_v1.0.0.xml',
    '06': 'out_transport_v1.1.0.xml',
    '07': 'out_withholding_v1.0.0.xml',
    '18': 'out_invoice_v2.1.0.xml',
}

SITE_BASE_TEST = 'https://celcer.sri.gob.ec/'
SITE_BASE_PROD = 'https://cel.sri.gob.ec/'
WS_TEST_RECEIV = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
WS_TEST_AUTH = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
WS_RECEIV = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
WS_AUTH = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'


def chek_reception(env='test'):
    if env == 'test':
        URL = WS_TEST_RECEIV
    else:
        URL = WS_RECEIV
    return check_service(URL)


def chek_autorization(env='test'):
    if env == 'test':
        URL = WS_TEST_AUTH
    else:
        URL = WS_AUTH
    return check_service(URL)


def check_service(URL=''):
    flag = False
    try:
        res = requests.get(URL)
        flag = True if res.status_code == 200 else False
    except requests.exceptions.RequestException:
        flag = False
    return flag


def _moduledir():
    return os.path.dirname(os.path.dirname(os.path.abspath(sys.modules[__name__].__file__)))


def _get_type_document(code):
    tmpl_path = os.path.join(_moduledir(), 'static', 'src', 'templates')
    env = Environment(loader=FileSystemLoader(tmpl_path))
    doc_tmpl = env.get_template(TEMPLATES[code])
    return doc_tmpl


def _info_tributary(document):
    company = document.company_id
    position_id = company.partner_id.property_account_position_id
    infoTributaria = {
        'ambiente': 1 if company.environment == 'test' else 2,
        'tipoEmision': 1,
        'razonSocial': fix_chars(company.name),
        'ruc': company.partner_id.vat,
        'codDoc': document.type_document_id.code_doc_xml,
        'estab': document.authorization_id.entity,
        'ptoEmi': document.authorization_id.issue,
        'secuencial': document.number,
        'dirMatriz': fix_chars('%s' % company.partner_id._display_address() or ''),
    }
    if document.authorization_id.establishment_id:
        establishment = document.authorization_id.establishment_id
        infoTributaria.update({'nombreComercial': fix_chars(establishment.name)})
    elif company.comercial_name:
        infoTributaria.update({'nombreComercial': fix_chars(company.comercial_name)})
    if position_id:
        if position_id.agent:
            infoTributaria.update({'agenteRetencion': position_id.code})
        if position_id.option == 'micro':
            infoTributaria.update({'regimenMicroempresas': position_id.name})
        if position_id.option == 'rimpe':
            infoTributaria.update({'contribuyenteRimpe': position_id.name})
    return infoTributaria


def fix_date(date):
    return time.strftime('%d/%m/%Y', time.strptime(date, '%Y-%m-%d'))


def fix_chars(code):
    new = [
        [u'á', 'a'],
        [u'é', 'e'],
        [u'í', 'i'],
        [u'ó', 'o'],
        [u'ú', 'u'],
        [u'Á', 'A'],
        [u'É', 'E'],
        [u'Í', 'I'],
        [u'Ó', 'O'],
        [u'Ú', 'U'],
        [u'-', ' '],
    ]
    special = [
        ['\n', ' '],
        [u'%', ' '],
        [u'º', ' '],
        [u'+', 'y'],
        [u'<', ' '],
        [u'>', ' '],
        [u',', ' '],
        [u'&', 'y'],
    ]
    for f, r in special:
        code = code.replace(f, r)
    return code

