#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64

from lxml import etree
from datetime import datetime, timedelta

from odoo import models, api, fields, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import code

summary_text = {
    1: _('VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA DIFERENTE DE CERO'),
    2: _('VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA DIFERENTE DE CERO'),
    3: _('IVA GENERADO EN LA DIFERENCIA ENTRE VENTAS Y NOTAS DE CREDITO CON DISTINTA TARIFA (AJUSTE A PAGAR)'),
    4: _('IVA GENERADO EN LA DIFERENCIA ENTRE VENTAS Y NOTAS DE CREDITO CON DISTINTA TARIFA (AJUSTE A FAVOR)'),
    5: _('VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA 0% QUE NO DAN DERECHO A CRÉDITO TRIBUTARIO'),
    6: _('VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA 0% QUE NO DAN DERECHO A CRÉDITO TRIBUTARIO'),
    7: _('VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA 0% QUE DAN DERECHO A CRÉDITO TRIBUTARIO'),
    8: _('VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA 0% QUE DAN DERECHO A CRÉDITO TRIBUTARIO'),
    9: _('EXPORTACIONES DE BIENES'),
    10: _('EXPORTACIONES DE SERVICIOS Y/O DERECHOS'),
    11: _('TOTAL VENTAS Y OTRAS OPERACIONES'),
    12: _('TRANSFERENCIAS NO OBJETO O EXENTAS DE IVA'),
    13: _('NOTAS DE CRÉDITO TARIFA 0% POR COMPENSAR PRÓXIMO MES'),
    14: _('NOTAS DE CRÉDITO TARIFA DIFERENTE DE CERO POR COMPENSAR PRÓXIMO MES'),
    15: _('INGRESOS POR REEMBOLSO COMO INTERMEDIARIO/VALORES FACTURADOS POR OPERADORAS DE TRANSPORTE (INFORMATIVO)'),
    16: _('ADQUISICIONES Y PAGOS (EXCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA DIFERENTE DE CERO (CON DERECHO A CRÉDITO TRIBUTARIO)'),
    17: _('ADQUISICIONES LOCALES DE ACTIVOS FIJOS GRAVADOS TARIFA DIFERENTE DE CERO(CON DERECHO A CRÉDITO TRIBUTARIO)'),
    18: _('OTRAS ADQUISICIONES Y PAGOS GRAVADOS TARIFA DIFERENTE DE CERO (SIN DERECHO A CRÉDITO TRIBUTARIO)'),
    19: _('IMPORTACIONES DE SERVICIOS Y/O DERECHOS GRAVADOS TARIFA DIFERENTE DE CERO'),
    20: _('IMPORTACIONES DE BIENES (EXCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA DIFERENTE DE CERO'),
    21: _('IMPORTACIONES DE SERVICIOS Y/O DERECHOS GRAVADOS TARIFA DIFERENTE DE CERO'),
    22: _('IMPORTACIONES DE BIENES (INCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA 0%'),
    23: _('ADQUISICIONES Y PAGOS (INCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA 0%'),
    24: _('ADQUISICIONES REALIZADAS A CONTRIBUYENTES RISE'),
    25: _('TOTAL ADQUISICIONES Y PAGOS'),
    26: _('ADQUISICIONES NO OBJETO DE IVA'),
    27: _('ADQUISICIONES EXENTAS DEL PAGO DE IVA'),
    28: _('NOTAS DE CRÉDITO TARIFA 0% POR COMPENSAR PRÓXIMO MES'),
    29: _('NOTAS DE CRÉDITO TARIFA  DIFERENTE DE CERO POR COMPENSAR PRÓXIMO MES'),
    30: _('PAGOS NETOS POR REEMBOLSO COMO INTERMEDIARIO / VALORES FACTURADOS POR SOCIOS A OPERADORAS DE TRANSPORTE'),
    31: _('IVA GENERADO EN LA DIFERENCIA ENTRE ADQUISICIONES Y NOTAS DE CRÉDITO CON DISTINTA TARIFA (AJUSTE EN POSITIVO AL CRÉDITO'),
    32: _('IVA GENERADO EN LA DIFERENCIA ENTRE ADQUISICIONES Y NOTAS DE CRÉDITO CON DISTINTA TARIFA (AJUSTE EN NEGATIVO AL CRÉDITO'),
    
}


cs_refund = {
    411: 1,
    412: 2,
    413: 5,
    414: 6,
    415: 7,
    416: 8,
    417: 9,
    418: 10,
    419: 11,
    441: 12,
    444: 15
}

cp_refund = {
    510: 1,
    511: 2,
    512: 3,
    513: 4,
    514: 5,
    515: 6,
    516: 7,
    517: 8,
    518: 9,
    519: 10,
    541: 11,
    542: 13,
    543: 14,
    544: 14,
    545: 14,    
}

code_104 = {
    31: _('31'),
    101: _('Mes'),
    102: _('Año'),
    104: _('N° Formulario que sustituye'),
    198: _('No ID Sujeto Pasivo/Representante Legal'),
    199: _('RUC Contador'),
    201: _('Cédula de identidad o no. de pasaporte del representante legal'),
    202: _('RAZÓN SOCIAL O APELLIDOS Y NOMBRES COMPLETOS'),
    401: 1,
    402: 2,
    403: 5,
    404: 6,
    405: 7,
    406: 8,
    407: 9,
    408: 10,
    409: 11,
    431: 12,
    434: 15,
    421: 1,
    422: 2,
    423: 3,
    424: 4,
    429: 11,
    453: 14,
    454: 15,
    480: _('TOTAL TRANSFERENCIAS GRAVADAS TARIFA DIFERENTE DE CERO A CONTADO ESTE MES'),
    481: _('TOTAL TRANSFERENCIAS GRAVADAS TARIFA DIFERENTE DE CERO A CRÉDITO ESTE MES'),
    482: _('TOTAL IMPUESTO GENERADO'),
    483: _('IMPUESTO A LIQUIDAR DEL MES ANTERIOR'),
    484: _('IMPUESTO A LIQUIDAR EN ESTE MES'),
    485: _('IMPUESTO A LIQUIDAR EN EL PRÓXIMO MES'),
    499: _('TOTAL IMPUESTO A LIQUIDAR EN ESTE MES'),
    500: 16,
    501: 17,
    502: 18,
    503: 19,
    504: 20,
    505: 21,
    506: 22,
    507: 23,
    508: 24,
    509: 25,
    531: 26,
    532: 27,
    535: 30,
    520: 16,
    521: 17,
    522: 18,
    523: 19,
    524: 20,
    525: 21,
    526: 31,
    527: 32,
    529: 25,
    554: 29,
    555: 30,
    563: _('FACTOR DE PROPORCIONALIDAD PARA CRÉDITO TRIBUTARIO'),
    564: _('CRÉDITO TRIBUTARIO APLICABLE EN ESTE PERÍODO'),
    601: _('IMPUESTO CAUSADO'),
    602: _('CRÉDITO TRIBUTARIO APLICABLE EN ESTE PERÍODO'),
    603: _('(-) COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS CON MEDIO ELECTRÓNICO'),
    604: _('(-) COMPENSACIÓN DE IVA POR VENTAS  EFECTUADAS EN  ZONAS AFECTADAS LEY DE SOLIDARIDAD'),
    605: _('POR ADQUISICIONES E IMPORTACIONES'),
    606: _('POR RETENCIONES EN LA FUENTE DE IVA QUE LE HAN SIDO EFECTUADAS'),
    607: _('POR COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS CON MEDIO  ELECTRÓNICO'),
    608: _('POR COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS EN ZONAS AFECTADAS  LEY DE SOLIDARIDAD'),
    609: _('(-)RETENCIONES EN LA FUENTE DE IVA QUE LE HAN SIDO EFECTUADAS EN ESTE PERÍODO'),
    610: _('(+) AJUSTE POR IVA DEVUELTO O DESCONTADO POR ADQUISICIONES EFECTUADAS CON MEDIO ELECTRÓNICO'),
    611: _('(+) AJUSTE POR IVA DEVUELTO O DESCONTADO EN ADQUISICIONES EFECTUADAS EN ZONAS AFECTADAS - LEY DE SOLIDARIDAD'),
    612: _('(+) AJUSTE POR IVA DEVUELTO E IVA RECHAZADO IMPUTABLE AL CRÉDITO TRIBUTARIO EN EL MES'),
    613: _('(+) AJUSTE POR IVA DEVUELTO E IVA RECHAZADO IMPUTABLE AL CRÉDITO TRIBUTARIO EN EL MES'),
    614: _('(+) AJUSTE POR IVA DEVUELTO POR OTRAS INSTITUCIONES DEL SECTOR PÚBLICO IMPUTABLE AL CRÉDITO TRIBUTARIO EN EL MES'),
    615: _('POR ADQUISICIONES E IMPORTACIONES'),
    617: _('POR RETENCIONES EN LA FUENTE DE IVA QUE LE HAN SIDO EFECTUADAS'),
    618: _('POR COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS CON MEDIO ELECTRÓNICO'),
    619: _('POR COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS EN ZONAS AFECTADAS  LEY DE SOLIDARIDAD'),
    620: _('SUBTOTAL A PAGAR'),
    621: _('IVA PRESUNTIVO DE SALAS DE JUEGO (BINGO MECÁNICOS) Y OTROS JUEGOS DE AZAR'),
    699: _('TOTAL IMPUESTO A PAGAR POR PERCEPCION'),
    721: _('RETENCIÓN DEL 10%'),
    723: _('RETENCIÓN DEL 20%'),
    725: _('RETENCIÓN DEL 30%'),
    727: _('RETENCIÓN DEL 50%'),
    729: _('RETENCIÓN DEL 70%'),
    731: _('RETENCIÓN DEL 100%'),
    799: _('TOTAL IMPUESTO RETENIDO'),
    800: _('DEVOLUCIÓN PROVISIONAL DE IVA MEDIANTE COMPENSACIÓN CON RETENCIONES EFECTUADAS '),
    801: _('TOTAL IMPUESTO A PAGAR POR RETENCIÓN'),
    859: _('TOTAL CONSOLIDADO DE IMPUESTO AL VALOR AGREGADO'),
    890: _('PAGO PREVIO'),
    897: _('INTERÉS'),
    898: _('IMPUESTO'),
    899: _('MULTA'),
    880: _('PAGO DIRECTO EN CUENTA ÚNICA DEL TESORO NACIONAL (Uso Exclusivo para Instituciones y Empresas del Sector Público Autorizadas)'),
    902: _('TOTAL IMPUESTO A PAGAR'),
    903: _('INTERÉS POR MORA'),
    904: _('MULTA'),
    999: _('TOTAL PAGADO'),
    905: _('MEDIANTE CHEQUE, DÉBITO BANCARIO, EFECTIVO U OTRAS FORMAS DE PAGO'),
    906: _('MEDIANTE COMPENSACIONES'),
    907: _('MEDIANTE NOTAS DE CRÉDITO'),
    925: _('MEDIANTE TÍTULOS DEL BANCO CENTRAL (TBC)'),
    908: _('N/C No'),
    909: _('Valor USD'),
    910: _('N/C No'),
    911: _('Valor USD'),
    912: _('N/C No'),
    913: _('Valor USD'),
    915: _('Valor USD'),
    916: _('Resolución No'),
    917: _('Valor USD'),
    918: _('Resolución No'),
    919: _('Valor USD'),
    920: _('Valor USD'),
}
'''    921: _('Forma de Pago'),
    922: _('Banco'),'''

class Form104(models.TransientModel):
    _name = 'form.104'
    _description = 'Form 104'
    
    @api.model
    def _get_month_how(self):
        date_how = fields.Date.context_today(self)
        return int(date_how[5:7])
    
    list_month = fields.Selection(selection=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], 
                                  string='Month', default=_get_month_how)
    type_form = fields.Selection(selection=[('O', 'Orignal'), ('S', 'Substitute')], string='Form Type', default='O')
    number_form =  fields.Char('N° Form Substitute', size=15, help='Enter in this field the number of the declaration form that is substituted')
    code_483 = fields.Float('After Code 483', default=0.0, help='Tax to settle from the previous month (Move field 485 from the previous statement)')
    date_start = fields.Date('Start Date', required=True)
    date_end = fields.Date('End Date')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    attachment_ids = fields.Many2many('ir.attachment', 'form_104_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments')


    @api.model
    def default_get(self, default_fields):
        res = super(Form104, self).default_get(default_fields)
        if not res.get('date_start', False) or not res.get('date_end', False):
            res.update(self._get_compute_dates(res.get('list_month')))
        return res


    @api.onchange('list_month','date_start')
    def onchange_list_month(self):
        if self.list_month:
            dict_date =  self._get_compute_dates(self.list_month)
            self.date_start = dict_date.get('date_start', False)
            self.date_end = dict_date.get('date_end', False)


    def _get_compute_dates(self, last_month):
        if not last_month:
            return {}
        date_old = fields.Date.context_today(self)
        if self.date_start:
            if date_old != self.date_start:
                date = datetime.strptime(self.date_start, DF)
            else:
                date = datetime.strptime(fields.Date.context_today(self), DF)
        else:
            date = datetime.strptime(fields.Date.context_today(self), DF)
        date_to = date
        if last_month == 2:
            date_to = date.replace(day=28, month=last_month, year=date.year)
        else:
            date = date.replace(day=30, month=last_month)
            date_to = date
        
        last_day = 1
        if last_month == 2 and date.day == 29 and (date.year) % 4 != 0:
            date = date.replace(month=last_month, day=28, year=date.year)
        else:
            date = date.replace(month=last_month, day=last_day, year=date.year)
        date_from = date
        if date_from.month == 2 and date_to.day == 29:
            date_from = date_from.replace(day=28, year=date_to.year)
        if last_month in [1, 3, 5, 7, 8, 10, 12]:
            date_to = date_to + timedelta(days=1)
        return {'date_start': date_from, 'date_end': date_to}


    @api.multi
    def generate_detail_xlxs(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'form.104')
        data['form'] = self.read(['date_start', 'date_end', 'company_id'])
        return self.env.ref('oe_account.form_104_xlsx').report_action(self, data=data)


    @api.multi
    def generate_xml(self):
        self.ensure_one()
        data = self.read(['date_start', 'date_end', 'company_id', 'code_483'])[0]
        form_104 = etree.Element('formulario')
        form_104.set('version', '0.2')
        header = etree.Element('cabecera')
        etree.SubElement(header, 'codigo_version_formulario').text = '04201701'
        etree.SubElement(header, 'ruc').text = self.company_id.vat
        etree.SubElement(header, 'codigo_moneda').text = '1'
        form_104.append(header)
        details_104 = etree.Element('detalle')
        
        result_code = _get_details_form_104(self, data)
        result_code[31][0] = self.type_form
        result_code[101][0] = int(data['date_start'][5:7])
        result_code[102][0] = int(data['date_start'][:4])
        result_code[104][0] = self.number_form if self.number_form else ''
        result_code[198][0] = ''
        result_code[199][0] = self.company_id.vat
        result_code[201][0] = self.company_id.vat
        result_code[202][0] = self.company_id.name
        
        for key in sorted(result_code):
            total = result_code[key]
            line = etree.SubElement(header, 'campo')
            line.set('numero', str(key))
            line.text = str(total[0])
            details_104.append(line)
        
        form_104.append(details_104)
        data_xml = etree.tostring(form_104, pretty_print=True, encoding='utf-8', xml_declaration=True, standalone=False)
        name = '%s-%s-%s' % ('104', self.date_start[0:4], self.date_end[5:7])
        attach = self.add_attachment(data_xml, name)
        self.attachment_ids = [(6, 0, [attach.id])]
        print(data_xml)
        return { "type": "ir.actions.do_nothing"}
            
    
    def add_attachment(self, xml_element, name):
        xml_encode = base64.encodebytes(xml_element)
        attach = self.env['ir.attachment'].create(
            {
                'name': '{0}.xml'.format(name),
                'datas': xml_encode,
                'datas_fname':  '{0}.xml'.format(name),
                'res_model': self._name,
                'res_id': self.id,
                'type': 'binary'
            },
        )
        return attach


class Form104Xlsx(models.TransientModel):
    _name = 'report.oe_account.form_104_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    
    def generate_xlsx_report(self, workbook, data, objects):
        data = {
            'company_id': (objects.company_id.id, objects.company_id.name),
            'date_start': objects.date_start,
            'date_end': objects.date_end,
            'code_483': objects.code_483
        }
        
        worksheet = self._get_default_settings_xlsx(workbook, 'Ventas')
        row = 0
        worksheet.set_column(0, 0, 60)
        worksheet.set_column(1, 1, 30)
        worksheet.set_column(2, 2, 15)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 15)
        worksheet.set_column(5, 5, 15)
        worksheet.set_column(6, 6, 15)
        worksheet.write_string(row, 0, u'Descripción')
        worksheet.write_string(row, 1, u'Casillero')
        worksheet.write_string(row, 2, u'Cantidad')
        worksheet.write_string(row, 3, u'P. Unitario')
        worksheet.write_string(row, 4, u'ICE')
        worksheet.write_string(row, 5, u'IVA')
        worksheet.write_string(row, 6, u'Valor')
        row += 1
        details_result = _get_details_form_104(self, data)
        code_104.update(cs_refund)
        code_104.update(cp_refund)
        for line in sorted(details_result.keys(), key=lambda x: x):
            if details_result[line][0] > 0.0:
                key_text = summary_text[code_104[line]] if code_104[line] in summary_text else code_104[line]
                worksheet.write_string(row, 0, key_text)
                worksheet.write_string(row, 1, str(line))
                worksheet.write_number(row, 6, details_result[line][0])
                row += 1
                if len(details_result[line][1]) >= 1:
                    for dline in details_result[line][1]:
                        worksheet.write_string(row, 0, dline.get('invoice', ''))
                        worksheet.write_string(row, 1, dline.get('product', ''))
                        worksheet.write_number(row, 2, dline.get('qty', 0.0))
                        worksheet.write_number(row, 3, dline.get('price_unit', 0.0))
                        worksheet.write_number(row, 4, dline.get('ice', 0.0))
                        worksheet.write_number(row, 5, dline.get('iva', 0.0))
                        worksheet.write_number(row, 6, dline.get('subtotal', 0.0))
                        row += 1
        workbook.close()


    def _get_default_settings_xlsx(self, workbook, name):
        worksheet = workbook.add_worksheet(name)
        worksheet.fit_to_pages(1, 0)
        worksheet.set_zoom(100)
        return worksheet


def _get_details_form_104(self, data):
    
    type_document = self.env['account.type.document']
    company_id = self.env['res.company'].browse(data['company_id'][0])
    domain = [('company_id', '=', company_id.id), ('date_invoice', '>=', data['date_start']), ('date_invoice', '<=', data['date_end']), ('state', 'in', ['open', 'paid'])]
    
    details_code = {}
    for x in code_104:
        details_code[x] = {0: 0.0, 1: []}
    sum_total_484 = 0.0
    
    type_ids = type_document.search([('code', '=', '18')])
    out_invoices = self.env['account.invoice'].search(domain + [('type', '=', 'out_invoice'), ('type_document_id', 'in', type_ids.ids)])
    
    for inv_o in out_invoices:
        if inv_o.payment_term_id:
            details_code[481][0] += inv_o.amount_subtotal
        else:
            details_code[480][0] += inv_o.amount_subtotal
        
        for line_o in inv_o.invoice_line_ids:
            amount_iva = 0.0
            amount_ice = 0.0
            amount_base = 0.0
            for code in line_o.invoice_line_form_code_ids:
                key = int(code.name)
                tax_group = _get_line_taxes(inv_o, line_o, key)
                for ktax in tax_group:
                    if tax_group[ktax]['grupo'] == 'iva':
                        amount_base += tax_group[ktax]['base']
                        amount_iva += tax_group[ktax]['amount']
                    if tax_group[ktax]['grupo'] == 'iva0':
                        amount_base += tax_group[ktax]['base']
                    if tax_group[ktax]['grupo'] == 'ice':
                        amount_ice += tax_group[ktax]['amount']
                details_code[key][0] += amount_base
                details_code[key][1] += [_get_line(line_o, amount_iva, amount_ice, amount_base)]
                if key == 401: details_code[421][0] += amount_iva
                if key == 402: details_code[422][0] += amount_iva

    for x in details_code:
        if x in [401, 402, 403, 404, 405, 406, 407, 408]:
            details_code[409][0] += details_code[x][0]
    
    refund = {}
    for x in cs_refund:
        refund[x] = {0: 0.0, 1: []}
        details_code[x] = {0: 0.0, 1: []}

    type_ids = type_document.search([('code', '=', '04')])
    out_refunds = self.env['account.invoice'].search(domain + [('type', '=', 'out_refund'), ('type_document_id', 'in', type_ids.ids)])
    
    for ref_o in out_refunds:
        if ref_o.refund_invoice_id:
            if ref_o.refund_invoice_id.payment_term_id:
                details_code[481][0] -= ref_o.refund_invoice_id.amount_subtotal
            else:
                details_code[480][0] -= ref_o.refund_invoice_id.amount_subtotal
        for line_r in ref_o.invoice_line_ids:
            amount_iva = 0.0
            amount_ice = 0.0
            amount_base = 0.0
            for code in line_r.invoice_line_form_code_ids:
                key = int(code.name)
                if key in refund.keys():
                    tax_group = _get_line_taxes(ref_o, line_r, key)
                    for ktax in tax_group:
                        if tax_group[ktax]['grupo'] == 'iva':
                            amount_base += tax_group[ktax]['base']
                            amount_iva += tax_group[ktax]['amount']
                        if tax_group[ktax]['grupo'] == 'iva0':
                            amount_base += tax_group[ktax]['base']
                        if tax_group[ktax]['grupo'] == 'ice':
                            amount_ice += tax_group[ktax]['amount']
                    if key == 411: details_code[421][0] -= amount_iva
                    if key == 412: details_code[422][0] -= amount_iva
                    refund[key][0] += amount_base
                    details_code[key][1] += [_get_line(line_r, amount_iva, amount_ice, amount_base)]

    details_code[411][0] = details_code[401][0] - refund[411][0]
    details_code[412][0] = details_code[402][0] - refund[412][0]
    details_code[413][0] = details_code[403][0] - refund[413][0]
    details_code[414][0] = details_code[404][0] - refund[414][0]
    details_code[415][0] = details_code[405][0] - refund[415][0]
    details_code[416][0] = details_code[406][0] - refund[416][0]
    details_code[417][0] = details_code[407][0] - refund[417][0]
    details_code[418][0] = details_code[408][0] - refund[418][0]
    
    for x in details_code:
        if x in [411, 412, 413, 414, 415, 416, 417, 418]:
            details_code[419][0] += details_code[x][0]

    details_code[429][0] = details_code[421][0] + details_code[422][0] + details_code[423][0] - details_code[424][0]
    details_code[453][0] = 0.0
    details_code[454][0] = 0.0
    details_code[482][0] = details_code[429][0]
    details_code[483][0] = data['code_483']
    details_code[484][0] = sum_total_484
    details_code[485][0] = details_code[482][0] + details_code[484][0]
    details_code[499][0] = details_code[483][0] + details_code[484][0]
    
    type_ids = type_document.search([('code', '=', '01')])
    in_invoices = self.env['account.invoice'].search(domain + [('type', '=', 'in_invoice')])
    
    for inv_i in in_invoices:
        for line_i in inv_i.invoice_line_ids:            
            amount_iva = 0.0
            amount_ice = 0.0
            amount_base = 0.0
            for code in line_i.invoice_line_form_code_ids:
                key = int(code.name)
                if key in details_code.keys():
                    tax_group = _get_line_taxes(inv_i, line_i, key)
                    for ktax in tax_group:
                        if tax_group[ktax]['grupo'] == 'iva':
                            amount_base += tax_group[ktax]['base']
                            amount_iva += tax_group[ktax]['amount']
                        if tax_group[ktax]['grupo'] == 'iva0':
                            amount_base += tax_group[ktax]['base']
                        if tax_group[ktax]['grupo'] == 'ice':
                            amount_ice += tax_group[ktax]['amount']
                    details_code[key][0] += amount_base
                    details_code[key][1] += [_get_line(line_i, amount_iva, amount_ice, amount_base)]
                    if key == 500: details_code[520][0] += amount_iva
                    if key == 501: details_code[521][0] += amount_iva
                    if key == 502: details_code[522][0] += amount_iva
                    if key == 503: details_code[523][0] += amount_iva
                    if key == 504: details_code[524][0] += amount_iva
                    if key == 505: details_code[525][0] += amount_iva
        
        for line in inv_i.withholding_id.withholding_line_ids:
            if line.name == 'renta_iva':
                details_code[721][0] += line.amount if line.tax_id.amount == -10 else 0.0
                details_code[723][0] += line.amount if line.tax_id.amount == -20 else 0.0
                details_code[725][0] += line.amount if line.tax_id.amount == -30 else 0.0
                details_code[727][0] += line.amount if line.tax_id.amount == -50 else 0.0
                details_code[729][0] += line.amount if line.tax_id.amount == -70 else 0.0
                details_code[731][0] += line.amount if line.tax_id.amount == -100 else 0.0
    
    for x in details_code:
        if x >= 500 and x <= 508: 
            details_code[509][0] += details_code[x][0]

    type_ids = type_document.search([('code', '=', '04')])
    in_refunds = self.env['account.invoice'].search(domain + [('type', '=', 'in_refund')])
    
    refund_purchase = {}
    for x in cp_refund:
        refund_purchase[x] = {0: 0.0, 1: []}
        details_code[x] = {0: 0.0, 1: []}
        
    for ref_i in in_refunds:
        for line_r in ref_i.invoice_line_ids:
            amount_iva = 0.0
            amount_ice = 0.0
            amount_base = 0.0
            for code in line_r.invoice_line_form_code_ids:
                key = int(code.name)
                if key in refund_purchase.keys():
                    tax_group = _get_line_taxes(ref_i, line_r, key)
                    for ktax in tax_group:
                        if tax_group[ktax]['grupo'] == 'iva':
                            amount_base += tax_group[ktax]['base']
                            amount_iva += tax_group[ktax]['amount']
                        if tax_group[ktax]['grupo'] == 'iva0':
                            amount_base += tax_group[ktax]['base']
                        if tax_group[ktax]['grupo'] == 'ice':
                            amount_ice += tax_group[ktax]['amount']
                    refund_purchase[key][0] += amount_base
                    details_code[key][1] += [_get_line(line_r, amount_iva, amount_ice, amount_base)]
                    if key == 510: details_code[520][0] -= amount_iva
                    if key == 511: details_code[521][0] -= amount_iva
                    if key == 512: details_code[522][0] -= amount_iva
                    if key == 513: details_code[523][0] -= amount_iva
                    if key == 514: details_code[524][0] -= amount_iva
                    if key == 515: details_code[525][0] -= amount_iva
    
    for x in refund_purchase:
        if x >= 510 and x <= 518: 
            refund_purchase[519][0] += refund_purchase[x][0]
    
    details_code[510][0] = details_code[500][0] - refund_purchase[510][0]
    details_code[511][0] = details_code[501][0] - refund_purchase[511][0]
    details_code[512][0] = details_code[502][0] - refund_purchase[512][0]
    details_code[513][0] = details_code[503][0] - refund_purchase[513][0]
    details_code[514][0] = details_code[504][0] - refund_purchase[514][0]
    details_code[515][0] = details_code[505][0] - refund_purchase[515][0]
    details_code[516][0] = details_code[506][0] - refund_purchase[516][0]
    details_code[517][0] = details_code[507][0] - refund_purchase[517][0]
    details_code[518][0] = details_code[508][0] - refund_purchase[518][0]

    details_code[526][0] = 0.0
    details_code[527][0] = 0.0
    details_code[529][0] = details_code[521][0] + details_code[522][0] + details_code[523][0] + details_code[525][0] + details_code[526][0] - details_code[527][0]
    details_code[554][0] = 0.0
    details_code[555][0] = 0.0
    
    tmp_419 = 1 if details_code[419][0] == 0 else details_code[419][0]
    tmp_sum_563 = details_code[411][0] + details_code[412][0] + details_code[415][0] + details_code[416][0] + details_code[417][0] + details_code[418][0]
    tmp_result_563 = tmp_sum_563/tmp_419
    details_code[563][0] = tmp_result_563
    details_code[564][0] = (details_code[520][0] + details_code[521][0] + details_code[523][0] + details_code[524][0] + details_code[525][0] + details_code[526][0] - details_code[527][0])*tmp_result_563
    
    tmp_601 = details_code[499][0] - details_code[564][0]
    if tmp_601 > 0:
        details_code[601][0] = tmp_601
    elif tmp_601 < 0:
        details_code[602][0] = tmp_601
    
    for inv_sale in out_invoices:
        wh_sale = inv_sale.withholding_id
        if wh_sale: details_code[609][0] += wh_sale.amount_iva
    
    tmp_neg_620 = details_code[601][0] - details_code[602][0] - details_code[603][0] - details_code[604][0] - details_code[605][0] - details_code[606][0] - details_code[607][0] - details_code[608][0] - details_code[609][0]
    tmp_pos_620 = details_code[610][0] + details_code[611][0] + details_code[612][0] + details_code[613][0] + details_code[614][0]
    tmp_res_620 = tmp_neg_620 + tmp_pos_620
    details_code[620][0] = tmp_res_620 if tmp_res_620 > 0 else 0.0
    details_code[699][0] = details_code[620][0] + details_code[621][0]
    
    details_code[799][0] = abs(details_code[721][0] + details_code[723][0] + details_code[725][0] + details_code[727][0] + details_code[729][0] + details_code[731][0])
    details_code[801][0] = abs(details_code[799][0] - details_code[800][0])
    details_code[859][0] = details_code[699][0] + details_code[801][0]
    details_code[902][0] = details_code[859][0] - details_code[898][0]
    details_code[999][0] = details_code[902][0] + details_code[903][0] + details_code[904][0]
    return details_code
     
                
def _get_line(line, amount_iva, amount_ice, amount_base):
    line_data = {
        'invoice': line.invoice_id.name,
        'product': line.product_id.name or line.name,
        'qty': line.quantity,
        'price_unit': line.price_unit,
        'ice': amount_ice,
        'iva': amount_iva,
        'subtotal': amount_base
    }
    return line_data

    
def _get_line_taxes(inv, line, key_104):
    tax_grouped = {}
    taxes = list()
    amount_irbpnr = 0.0
    amount_iva = 0.0
    amount_ice = 0.0
    for tax in line.invoice_line_tax_ids:
        price_unit = line.price_unit if tax.tax_group_id.type == 'ice' else line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        price_unit = round(price_unit, 2)
        if tax.tax_group_id.type == 'irbpnr':
            amount_irbpnr += line.quantity
        else:
            tax_list = tax.compute_all(price_unit, inv.currency_id, line.quantity, line.product_id, inv.partner_id)['taxes'][0]
            if tax.tax_group_id.type == 'iva':
                amount_iva += tax_list['amount']
            if tax.tax_group_id.type == 'ice':
                amount_ice += tax_list['amount']
    
    for tax in line.invoice_line_tax_ids:
        price_unit = line.price_unit if tax.tax_group_id.type == 'ice' else line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        price_unit = round(price_unit, 2)
        if tax.tax_group_id.type == 'renta_iva':
            taxes += tax.with_context(base_values=[amount_iva, amount_iva, amount_iva]).compute_all(price_unit, inv.currency_id, line.quantity, line.product_id, inv.partner_id)['taxes']
        elif tax.tax_group_id.type == 'irbpnr':
            taxes += tax.with_context(base_values=[amount_irbpnr, amount_irbpnr, amount_irbpnr]).compute_all(price_unit, inv.currency_id, line.quantity, line.product_id, inv.partner_id)['taxes']
        elif tax.tax_group_id.type == 'iva':
            base_iva = price_unit * line.quantity + amount_ice
            taxes += tax.with_context(base_values=[base_iva, base_iva, base_iva]).compute_all(price_unit, inv.currency_id, line.quantity, line.product_id, inv.partner_id)['taxes']
        else:                    
            taxes += tax.compute_all(price_unit, inv.currency_id, line.quantity, line.product_id, inv.partner_id)['taxes']
    for tax in taxes:
        val = _prepare_tax_line_vals(inv, line, tax, key_104)
        key = inv.env['account.tax'].browse(tax['id']).get_grouping_key(val)

        if key not in tax_grouped:
            tax_grouped[key] = val
        else:
            tax_grouped[key]['amount'] += val['amount']
            tax_grouped[key]['base'] += val['base']
    return tax_grouped


def _prepare_tax_line_vals(inv, line, tax, key_104):
    """ Prepare values to create an account.invoice.tax line

    The line parameter is an account.invoice.line, and the
    tax parameter is the output of account.tax.compute_all().
    """
    tax_id = inv.env['account.tax'].browse(tax['id'])
    vals = {
        'invoice_id': inv.id,
        'type': tax_id.type_tax_use,
        'grupo': tax_id.tax_group_id.type,
        'casillero': key_104,
        'name': tax['name'],
        'tax_id': tax['id'],
        'amount': tax['amount'],
        'base': tax['base'],
        'manual': False,
        'sequence': tax['sequence'],
        'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
        'account_id': inv.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
    }

    # If the taxes generate moves on the same financial account as the invoice line,
    # propagate the analytic account from the invoice line to the tax line.
    # This is necessary in situations were (part of) the taxes cannot be reclaimed,
    # to ensure the tax move is allocated to the proper analytic account.
    if not vals.get('account_analytic_id') and line.account_analytic_id and vals['account_id'] == line.account_id.id:
        vals['account_analytic_id'] = line.account_analytic_id.id
    return vals