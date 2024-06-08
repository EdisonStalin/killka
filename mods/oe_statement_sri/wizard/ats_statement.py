# -*- coding: utf-8 -*-

import os
import sys
import time
import math
import base64
import logging

from lxml import etree
from itertools import groupby
from operator import itemgetter
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from jinja2 import Environment, FileSystemLoader
from lxml.etree import fromstring, DocumentInvalid


from odoo import models, api, fields, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError

typeIdentify = {
    'invalid': '00',
    'ruc': '04',
    'ruc_pri':'04',
    'ruc_pub':'04',
    'vat': '05',
    'passport': '06',
    'final_consumer': '07',
    'vat_exterior': '06',
    'license': '09',
}

typeSupplier = {
    'invalid': '00',
    'ruc': '01',
    'ruc_pri': '01',
    'ruc_pub': '01', 
    'vat' : '02',
    'passport' : '03',
    'final_consumer': '01',
    'vat_exterior': '03',
    'license': '01',
}


class AtsStatement(models.TransientModel):
    _name = 'ats.statement'
    _description = 'Ats the statement'


    @api.model
    def _get_month_how(self):
        date_how = fields.Date.context_today(self)
        return int(date_how[5:7])


    type_period = fields.Selection(selection=[('monthly', 'Monthly'),
                                              ('semester_1', 'Semester 1'),
                                              ('semester_2', 'Semester 2')], string='Period', default='monthly', required=True)
    list_month = fields.Selection(selection=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], 
                                  string='Month', default=_get_month_how)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    attachment_ids = fields.Many2many('ir.attachment', 'ats_statement_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments')


    @api.onchange('type_period', 'list_month','date_start')
    def onchange_list_month(self):
        dict_date = self._get_compute_dates(self.list_month)
        self.date_start = dict_date.get('date_start', False)
        self.date_end = dict_date.get('date_end', False)


    def _get_compute_dates(self, last_month):
        date_old = fields.Date.context_today(self)
        if self.type_period == 'semester_1': last_month = 1
        if self.type_period == 'semester_2': last_month = 7

        if self.date_start:
            if date_old != self.date_start:
                date = datetime.strptime(self.date_start, DF)
            else:
                date = datetime.strptime(date_old, DF)
        else:
            date = datetime.strptime(date_old, DF)
        
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
        if 'semester' in self.type_period:
            date_to = date_to + relativedelta(months=5)
            last_month = date_to.month
        if last_month in [1, 3, 5, 7, 8, 10, 12]:
            date_to = date_to + timedelta(days=1)
        return {'date_start': date_from, 'date_end': date_to}
    
    
    @api.multi
    def generate_xml(self):
        for att in self.attachment_ids:
            att.unlink()
        tmpl_path = os.path.join(self._moduledir(), 'static', 'src', 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ats_tmpl = env.get_template('ats_statement.xml')
        
        invoice_obj = self.env['account.invoice']
        data_ats = {}
        domain = [('state', 'in', ['open', 'paid']), ('date_invoice', '>=', self.date_start),\
                  ('date_invoice', '<=', self.date_end), ('company_id', '=', self.company_id.id)]
        out_invoices = invoice_obj.search(domain + [('type', 'in', ['out_invoice', 'out_refund'])])
        in_invoices = invoice_obj.search(domain + [('type', 'in', ['in_invoice', 'in_refund'])])
        
        data_ats.update(self._info_tributary(self.company_id, out_invoices))
        data_ats.update(self._get_in_invoice_refund(in_invoices))
        data_ats.update(self._get_out_invoice_refund(out_invoices))
        data_ats.update(self._get_entity(out_invoices))
        data_xml = ats_tmpl.render(data_ats)
        #print(data_xml)
        name = 'ATS-%s-%s' % (self.date_start[0:4], self.date_end[5:7])
        dir_schema = 'static/src/schemas/ats.xsd'
        #data_xml = self._ordenar(data_xml, dir_schema)
        print(data_xml)
        self.validate_xml(data_xml, dir_schema)
        attach = self.add_attachment(data_xml, name)
        self.attachment_ids = [(6, 0, [attach.id])]
        return { "type": "ir.actions.do_nothing"}
        
    
    def _info_tributary(self, company_id, out_invoices):
        if not company_id.vat: raise UserError(_('The company has not registered the RUC'))
        if not company_id.name: raise UserError(_('The company has not registered the business name'))
        total_sale = 0.0
        for x in out_invoices:
            if x.type_document_id.code in ['18', '05']:
                total_sale += (x.amount_untaxed_0 + x.amount_untaxed + 0)
            elif x.type_document_id.code in ['04']:
                total_sale += -(x.amount_untaxed_0 + x.amount_untaxed + 0)
        date = self.date_end if 'semester' in self.type_period else self.date_start
        iva = {
            'TipoIDInformante': 'R',
            'IdInformante': company_id.vat,
            'razonSocial': self.fix_chars(company_id.name),
            'Anio': str(date).split('-')[0],
            'Mes': str(date).split('-')[1],
            'numEstabRuc': company_id.code_business,
            'totalVentas': '%.2f' % total_sale,
            'codigoOperativo': 'IVA',
        }
        if 'semester' in self.type_period:
            iva.update({
                'regimenMicroempresa': 'SI',
            })
        return iva


    def _get_entity(self, out_lines):
        total_sale = 0
        for x in out_lines:
            if x.type_document_id.code in ['18', '05']:
                total_sale += (x.amount_untaxed_0 + x.amount_untaxed + 0)
            elif x.type_document_id.code in ['04']:
                total_sale += -(x.amount_untaxed_0 + x.amount_untaxed + 0)
        ventasEst = {
            'codEstab': '001',
            'ventasEstab': '%.2f' % total_sale,
            'ivaComp': '%.2f' % 0.0,
        }
        return {'ventasEst': [ventasEst]}


    def _get_in_invoice_refund(self, purchase_lines):
        detallesCompras = list()
        line = {}
        for x in purchase_lines:
            valRetBien10, valRetServ20, valorRetBienes, valRetServ50, valorRetServicios, valRetServ100 = self._get_amount_withholding_iva(x)
            if not x.partner_id.type_vat or typeIdentify[x.partner_id.type_vat] == 'invalid':
                raise UserError(_('The supplier %s is not active at validation check' % (x.partner_id.name)))
            if not x.partner_id.vat:
                raise UserError(_('The %s supplier does not have a registered RUC/Vat') % x.partner_id.name)
            line = {
                'codSustento': x.tax_support_id.code,
                'tpIdProv': typeSupplier[x.partner_id.type_vat],
                'idProv': x.partner_id.vat,
                'tipoComprobante': x.type_document_id.code,
                'tipoProv': x.partner_id.type_supplier,
                'denoProv': self.fix_chars(x.partner_id.name),
                'parteRel': 'NO' if x.type_document_id.code in ['01', '02', '03'] else 'NO',
                'fechaRegistro': time.strftime('%d/%m/%Y', time.strptime(x.date_invoice, '%Y-%m-%d')),
                'establecimiento': x.authorization_id.entity,
                'puntoEmision': x.authorization_id.issue,
                'secuencial': x.number,
                'fechaEmision': time.strftime('%d/%m/%Y', time.strptime(x.date_invoice, '%Y-%m-%d')),
                'autorizacion': x.access_key if x.is_electronic else x.authorization_id.name,
                'baseNoGraIva': '%.2f' % 0.0,
                'baseImponible': '%.2f' % x.amount_untaxed_0,
                'baseImpGrav': '%.2f' % x.amount_untaxed,
                'baseImpExe': '%.2f' % 0.0,
                'montoIce': '%.2f' % x.amount_ice,
                'montoIva': '%.2f' % x.amount_tax,
                'valRetBien10': '%.2f' % valRetBien10,
                'valRetServ20': '%.2f' % valRetServ20,
                'valorRetBienes': '%.2f' % valorRetBienes,
                'valRetServ50': '%.2f' % valRetServ50,
                'valorRetServicios': '%.2f' % valorRetServicios,
                'valRetServ100': '%.2f' % valRetServ100,
                'totbasesImpReemb': '%.2f' % 0.0,
                'pagoExterior': {
                    'pagoLocExt': '01',
                    'paisEfecPago': 'NA',
                    'aplicConvDobTrib': 'NA',
                    'pagoExtSujRetNorLeg': 'NA'
                },
                'formasDePago': [],      
            }
            if len(x.payment_ids):
                for pay in x.payment_ids:
                    line['formasDePago'] += [{'formaPago': pay.method_id.code}]
            else:
                line['formasDePago'] += [{'formaPago': '01'}]
                    
            if x.withholding_id and x.withholding_id.state == 'approved':
                line.update({'detalleAir': self.process_lines(x.withholding_id.withholding_line_ids)})
                if x.withholding_id.authorization:
                    line.update({'retencion': True})
                    line.update(self.get_withholding(x.withholding_id))
            
            if x.type == 'in_refund':
                inv = x.refund_invoice_id
                if not inv:
                    name = '%s-%s-%s' % (x.tmpl_entity, x.tmpl_emission, x.tmpl_number)
                    inv = self.env['account.invoice'].search([('name','=', name), ('company_id', '=', x.company_id.id)], limit=1)
                    if inv: x.write({'refund_invoice_id': inv.id})
                line.update({
                    'docModificado': inv.type_document_id.code,
                    'estabModificado': inv.authorization_id.entity,
                    'ptoEmiModificado': inv.authorization_id.issue,
                    'secModificado': inv.number,
                    'autModificado': inv.authorization_number if inv.is_electronic else inv.authorization_id.name,
                })
            detallesCompras.append(line)
        return {'compras': detallesCompras}

        
    def get_withholding(self, wh):
        data_wh = {
            'estabRetencion1': wh.authorization_id.entity,
            'ptoEmiRetencion1': wh.authorization_id.issue,
            'secRetencion1': wh.number,
            'autRetencion1': wh.authorization_number if wh.is_electronic and wh.authorization else wh.authorization_id.name,
            'fechaEmiRet1': time.strftime('%d/%m/%Y', time.strptime(wh.date_withholding, '%Y-%m-%d')),
        }
        return data_wh

    
    def _get_amount_withholding_iva(self, inv):
        valRetBien10 = 0.0
        valRetServ20 = 0.0
        valorRetBienes = 0.0
        valRetServ50 = 0.0
        valorRetServicios = 0.0
        valRetServ100 = 0.0
        for line in inv.tax_line_ids:
            if line.tax_id.tax_group_id.type == 'renta_iva':
                if line.tax_id.amount == -10: valRetBien10 += line.amount_total
                if line.tax_id.amount == -20: valRetServ20 += line.amount_total
                if line.tax_id.amount == -30: valorRetBienes += line.amount_total
                if line.tax_id.amount == -50: valRetServ50 += line.amount_total
                if line.tax_id.amount == -70: valorRetServicios += line.amount_total
                if line.tax_id.amount == -100: valRetServ100 += line.amount_total
        return abs(valRetBien10), abs(valRetServ20), abs(valorRetBienes), abs(valRetServ50), abs(valorRetServicios), abs(valRetServ100)


    def process_lines(self, lines):
        """
        @temp: {'332': {baseImpAir: 0,}}
        @data_air: [{baseImpAir: 0, ...}]
        """
        data_air = []
        temp = {}
        for line in lines:
            if line.name in ['renta']:
                key = line.tax_id.form_code_ats
                if not temp.get(key):
                    temp[key] = {
                        'baseImpAir': 0,
                        'valRetAir': 0
                    }
                temp[key]['baseImpAir'] += line.amount_base
                temp[key]['codRetAir'] = key
                amount_air = abs(line.tax_id.amount)
                dec, ent = math.modf(amount_air)
                temp[key]['porcentajeAir'] = int(amount_air) if dec==0 else amount_air
                temp[key]['valRetAir'] += abs(line.amount)
        for k, v in temp.items():
            temp[k]['baseImpAir'] = '%.2f' % temp[k]['baseImpAir']
            temp[k]['valRetAir'] = '%.2f' % temp[k]['valRetAir']
            data_air.append(v)
        return data_air
                
    
    def _get_out_invoice_refund(self, out_invoices):
        list_lines = []
        for sale in out_invoices:
            if not sale.partner_id.type_vat or typeIdentify[sale.partner_id.type_vat] == 'invalid':
                raise UserError(_('The client %s is not active at validation check' % (sale.partner_id.name)))
            if not sale.partner_id.vat: 
                raise UserError(_('The client %s does not have a registered RUC/Vat') % sale.partner_id.name)
            valorRetIva = 0.0
            valorRetRenta = 0.0
            if sale.withholding_id and sale.withholding_id.state== 'approved':
                valorRetIva = abs(sale.withholding_id.amount_iva)
                valorRetRenta = abs(sale.withholding_id.amount_renta)
            data = {
                'key': '%s-%s' % (sale.partner_id.vat, sale.type_document_id.code),
                'tpIdCliente': typeIdentify[sale.partner_id.type_vat],
                'idCliente': sale.partner_id.vat,
                'partner': sale.partner_id,
                'auth': sale.authorization_id,
                'tipoComprobante': sale.type_document_id.code,
                'tipoEmision': 'F',
                'numeroComprobantes': 1,
                'baseNoGraIva': 0.0,
                'baseImponible': sale.amount_untaxed_0,
                'baseImpGrav': sale.amount_untaxed,
                'montoIva': sale.amount_tax,
                'montoIce': sale.amount_ice,
                'valorRetIva': valorRetIva,
                'valorRetRenta': valorRetRenta,
                'formasDePago': []
            }
            if sale.type_document_id.code in ['18', '05']:
                if len(sale.payment_ids):
                    for pay in sale.payment_ids:
                        if not pay.method_id.code:
                            print("HOLA")
                        data['formasDePago'] += [{'formaPago': pay.method_id.code}]
                else:
                    data['formasDePago'] += [{'formaPago': '01'}]
            
            list_lines.append(data)
        list_lines = sorted(list_lines, key=itemgetter('key'))
        
        detalleVentas = list()
        for ruc, grupo in groupby(list_lines, key=itemgetter('key')):
            partner_temp = False
            auth_temp = False
            numeroComprobantes = 0
            baseNoGraIva = 0
            baseImponible = 0
            baseImpGrav = 0
            montoIva = 0
            montoIce = 0
            valorRetIva = 0
            valorRetRenta = 0
            list_payment = []
            for i in grupo:
                partner_temp = i['partner']
                auth_temp = i['auth']
                numeroComprobantes += 1
                baseNoGraIva += i['baseNoGraIva']
                baseImponible += i['baseImponible']
                baseImpGrav += i['baseImpGrav']
                montoIva += i['montoIva']
                montoIce += i['montoIce']
                valorRetIva += i['valorRetIva']
                valorRetRenta += i['valorRetRenta']
                list_payment += i['formasDePago']
            detalle = {
                'tpIdCliente': typeIdentify[partner_temp.type_vat],
                'idCliente': partner_temp.vat,
                'tipoComprobante': auth_temp.type_document_id.code,
                'tipoEmision': 'F',
                'numeroComprobantes': numeroComprobantes,
                'baseNoGraIva': '%.2f' % baseNoGraIva,
                'baseImponible': '%.2f' % baseImponible,
                'baseImpGrav': '%.2f' % baseImpGrav,
                'montoIva': '%.2f' % montoIva,
                'montoIce': '%.2f' % montoIce,
                'valorRetIva': '%.2f' % valorRetIva,
                'valorRetRenta': '%.2f' % valorRetRenta,
                'formasDePago': list_payment,
            }
            if typeIdentify[partner_temp.type_vat] in ['06']:
                detalle['denoCli'] = self.fix_chars(partner_temp.name)
            if detalle['tpIdCliente'] in ['04', '05', '06']:
                detalle['parteRelVtas'] = 'NO'
            if detalle['tpIdCliente'] not in ['04', '05', '07']:
                detalle['tipoCliente'] = typeIdentify[partner_temp.type_vat]
            detalleVentas.append(detalle)
        return {'ventas': detalleVentas}


    def add_attachment(self, xml_element, name):
        xml_ats = bytes(xml_element, 'utf-8')
        xml_encode = base64.encodebytes(xml_ats)
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

    
    def _ordenar(self, doc_xml, dir_schema):
        tmpl_path = os.path.join(self._moduledir(), dir_schema)
        file_xsd = open(tmpl_path).read()
        xml_code = bytes(file_xsd, 'utf-8')
        file_io_xsd = base64.encodebytes(xml_code)
        schema_doc = etree.parse(file_io_xsd)
        xschema = etree.XMLSchema(schema_doc)
        tipos = dict()
        for a in xschema.findall('./*'):
            b=a.attrib.get('name')
            tipos[b]=a
        droot= tipos.get(doc_xml.tag)
        if droot is not None:
            return self._ordenar2(doc_xml, droot, tipos)
        return doc_xml


    def _ordenar2(self, doc_xml, xschema_doc, tipos):
        dsort=dict()
        ass = xschema_doc.findall('./*')
        tipo = tipos.get(doc_xml.tag)
        
        if tipo is not None: ass.append(tipo)
        i=0
        j=0
        while(1):
            if (i >= len(ass)):
                break
            a=ass[i]
            i=i+1
            b=a.attrib.get('name')
            if not b:
                b = a.attrib.get('ref')

            ass.extend(a.findall('./*'))

            if b:
                dsort[b]=(j, a)
                j=j+1

        lista=list()
        for b in doc_xml.findall('./*'):
            lista.append([dsort.get(b.tag), b])

        if not lista: return doc_xml
        lista.sort()
        for a in lista:
            if a[0]:
                a[1]=self._ordenar2(a[1], a[0][1], tipos)
        doc_xml[:]=map(lambda x: x[1], lista)
        return doc_xml


    def validate_xml(self, document_xml, schema_doc):
        """
        Validar esquema XML
        """
        logger = logging.getLogger('oe_statement_sri.models.sri')
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding='UTF-8')
        document = fromstring(document_xml.encode('UTF-8'), parser=parser)
        logger.info('Validacion de esquema')
        logger.debug(etree.tostring(document, pretty_print=True))
        file_path = os.path.join(self._moduledir(), schema_doc)
        schema_file = open(file_path, 'rb')#.read().decode('ISO-8859-1')
        try:
            xmlschema_doc = etree.parse(schema_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            etree.XMLSchemaValidateError
            xmlschema.assertValid(document)
            return True
        except DocumentInvalid as err:
            msg = err.error_log.last_error.message or ''
            raise UserError('Invalid XML document error: %s, %s' % (err, msg))
        except etree.ParseError as err:
            msg = err.error_log.last_error.message or ''
            raise UserError('Invalid XML document error: %s, %s' % (err, msg))
        except etree.ParserError as err:
            msg = err.error_log.last_error.message or ''
            raise UserError('Invalid XML document error: %s, %s' % (err, msg))
        except etree.XMLSchemaValidateError as err:
            msg = err.error_log.last_error.message or ''
            raise UserError('Invalid XML document error: %s, %s' % (err, msg))
        except etree.XMLSyntaxError as err:
            msg = err.error_log.last_error.message or ''
            raise UserError('Invalid XML document error: %s, %s' % (err, msg))
        except:
            pass


    def _moduledir(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(sys.modules[__name__].__file__)))
    
    def fix_chars(self, code):
        special = [
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
            ['\n', ' '],
            [u'%', ' '],
            [u'º', ' '],
            [u'+', 'y'],
            [u'-', ' '],
            [u'Ñ', 'N'],
            [u'ñ', 'n'],
            [u'&', 'y'],
            [u'.', ' '],
            [u',', ' '],
            [u'(', ''],
            [u')', ''],
        ]
        for f, r in special:
            code = code.replace(f, r)
        return code
