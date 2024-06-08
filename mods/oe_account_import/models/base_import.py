# -*- coding: utf-8 -*-

import os
import re
import time
import zeep
import logging
import datetime
import itertools
import psycopg2
import xmltodict, json
from .sri_service import SriService
from jinja2 import Environment, FileSystemLoader
from dateutil.relativedelta import relativedelta
from odoo import models, api, fields, _
from odoo.tools import pycompat, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

ERROR_PREVIEW_BYTES = 200


FILE_TYPE_DICT = {
    'text/xml': ('xml', True, None),
    'text/plain': ('txt', True, None),
}

TYPE_MOVE = {
    'in_invoice': ('factura', 'Factura'),
    'in_refund': ('notaCredito', 'NotaCredito'),
    'in_debit': ('notaDebito', 'NotaDebito'),
    'in_withholding': ('comprobanteRetencion', 'CompRetencion'),
    'in_transport': ('guiaRemision', 'GuiaRemision'),
    'out_invoice': ('liquidacionCompra', 'LiquidacionCompra'),
}

TYPE_ENVIRON = {
    1: 'PRUEBAS',
    2: 'PRODUCCIÓN'
}

TYPE_TAX = {
    '1': 'renta',
    '2': 'iva',
    '3': 'ice',
    '5': 'irbpnr',
    '6': 'isd',
}

PER_TAX_IVA = {
    '0': 'iva0',
    '2': 'iva',
    '3': 'iva',
    '6': 'nobiva',
    '7': 'exiva',
}

EXPRESSION = {
    'out_invoice': ('^.*?Factura\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(\d{49})\t(\d{49})\t(.*?)\t(.*?)\s(.*?)\t(NORMAL)\t(.*?)$', 3, 8, 2, '^.*', 'date_invoice'),
    'in_invoice': ('^.*?Factura\s(\d{3}-\d{3}-\d{9})\t(\d{13})\t(.*?)\t(.*?)\t(.*?)\s(.*?)\s(NORMAL)\t\t(.*?)\t(\d{49})\t(\d{49})', 9, 1, 2, '^.*', 'date_invoice'),
    'out_withholding': ('^.*?Comprobante\sde\sRetenci.n\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(\d{49})\t(\d{49})\t(.*?)\t(.*?)\t(NORMAL)\t(\d{13})', 2, 1, 2, '^.*', 'date_withholding'),
    'in_withholding': ('^.*?Comprobante\sde\sRetenci.n\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(.*?)\t(.*?)\t(.*?)\t(NORMAL)\t(.*?)\t(.*?)\t(\d{49})\t(\d{49})', 9, 1, 2, '^.*', 'date_withholding'),
    'out_refund': ('^.*?Notas\sde\sCr.dito\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(.*?)\t(.*?)\t(.*?)\s(.*?)\s(NORMAL)\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(\d{49})\t(\d{49})$', 10, 1, 2, '^.*', 'date_invoice'),
    'in_refund': ('^.*?Notas\sde\sCr.dito\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(.*?)\t(.*?)\t(.*?)\s(.*?)\s(NORMAL)\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(\d{49})\t(\d{49})$', 10, 1, 2, '^.*', 'date_invoice'),
    'in_debit': ('^.*?Notas\sde\sD.dito\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(.*?)\t(.*?)\t(.*?)\s(.*?)\s(NORMAL)\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(\d{49})\t(\d{49})$', 10, 1, 2, '^.*', 'date_invoice'),
    'out_transport': ('^.*?Gu.as\sde\sRemisi.n\t(\d{3}-\d{3}-\d{9})\t(\d{13})\t(\d{49})\t(\d{49})\t(.*?)\t(.*?)\t(NORMAL)\t', 2, 1, 2, '^.*', 'date_emission'),
}

TYPE_DATE = {
    'in_invoice': 'date_invoice',
    'in_refund': 'date_invoice',
    'out_refund': 'date_invoice',
    'in_withholding': 'date_withholding',
    'in_transport': 'date_withholding',
    'out_invoice': 'date_invoice',
}

class Import(models.TransientModel):
    _inherit = 'base_import.import'

    type_document = fields.Char(string='Type Document', size=50)
    
    @api.multi
    def _read_file(self, options):
        (file_extension, handler, req) = FILE_TYPE_DICT.get(self.file_type, (None, None, None))
        if handler:
            try:
                return getattr(self, '_read_' + file_extension)(options)
            except Exception as e:
                _logger.warn("Failed to read file '%s' (transient id %d) using user-provided mimetype %s: %s", self.file_name or '<unknown>', self.id, self.file_type, e)
                raise ValueError(_("Unsupported file format \"{}\", import only supports XML SRI").format(self.file_type))
            if req and file_extension == 'xml':
                raise ImportError(_("Unable to load \"{extension}\" file: requires Python module \"{modname}\"").format(extension=file_extension, modname=req))
        return super(Import, self)._read_file(options)

    
    def _get_value_exist(self, previews, xkey):
        rows = []
        company = self.env.user.company_id.id
        obj_model = self.env[self.res_model]
        domain_document = [('type', '=', self.type_document), ('company_id', '=', company)]
        path = '/tmp/%s/' % self._cr.dbname
        if not os.path.isdir(path):
            os.makedirs(path, mode=0o777)
        for record in self.web_progress_iter(previews, msg=_('Reviewing the document'), total=len(previews), cancellable=True, log_level="debug"):
            document = obj_model.search(domain_document+[('authorization_number', '=', record[xkey])])
            if 'withholding' in self.type_document:
                record.insert(xkey + 1, record[6])
                del record[6]
            else:
                record[4] = '%s %s' % (record[4], record[5])
                del record[5]
            if not document:
                record.insert(0, _('NOT JOINED'))
                self._search_sri(record[xkey], path)
            else:
                record.insert(0, _('JOINED'))
            rows += [record]
        _logger.info(_('Document review completed satisfactorily.'))
        return rows


    @api.multi
    def _read_txt(self, options):
        rows = []
        txt_data = str(self.file, 'ISO-8859-1')
        lines_txt = txt_data.split('\n')
        (exp, xkey, xvat, xsal, aexp, typedoc) = EXPRESSION.get(self.type_document, (None, None, None, None, None, None))
        regexp = re.compile(exp)
        regexpalt = re.compile(aexp)
        recordx = 0
        for i in range(xsal, len(lines_txt)):
            line = lines_txt[i]
            if len(line) == 0: continue
            list_line = regexp.findall(line) if i%2 == 0 else regexpalt.findall(line)
            if len(list_line) == 0: continue
            if i%2 == 0:
                rows += [[x for x in list_line[0]]]
                recordx = len(rows) - 1
            else:
                rows[recordx] += list_line
        rows = self._get_value_exist(rows, xkey)
        _logger.info(_('Finish reading import.'))
        return rows


    @api.multi
    def _read_xml(self, options):
        xml_data = self.file.decode('utf-8')
        vals, error = self._get_review_xml(xml_data)
        partner_id = self.env['res.partner'].browse(vals['partner_id'])
        record = [_('NOT JOINED'), vals['name'], partner_id.vat, partner_id.name, vals[TYPE_DATE[self.type_document]], vals['authorization_date'],
                  vals['emission_code'], partner_id.company_id.name, vals['access_key'], vals['authorization_number'], vals['name']]
        rows = [record]
        return rows


    @api.multi
    def parse_preview(self, options, count=80):
        errors = []
        if 'date_format' in options: options['date_format'] = '%d/%m/%Y'
        try:
            if self.file_type not in ['text/xml', 'text/plain']:
                return super(Import, self).parse_preview(options, count)
            else:
                new_heards = ['reference', 'name', 'vat', 'partner_id', 'authorization_date', 'emission_code', 
                    'company_id', 'access_key', 'authorization_number', 'origin']
                new_heards.insert(4, TYPE_DATE[self.type_document])
                options['fields'] = new_heards
                fields = self.get_fields(self.res_model)
                fields += self.get_fields('res.partner')
                rows = self._read_file(options)
                matches = {index: [header] for index, header in enumerate(new_heards)}
                headers = new_heards
                # Match should have consumed the first row (iif headers), get
                # the ``count`` next rows for preview
                preview = list(itertools.islice(rows, count))
                assert preview, "CSV file seems to have no content"
                header_types = self._find_type_from_preview(options, preview)
                
                if options.get('keep_matches', False) and len(options.get('fields', [])):
                    matches = {}
                    for index, match in enumerate(options.get('fields')):
                        if match:
                            matches[index] = match.split('/')
                result_preview = {
                    'fields': fields,
                    'matches': matches or False,
                    'headers': headers or False,
                    'headers_type': header_types or False,
                    'preview': preview,
                    'options': options,
                    'debug': self.user_has_groups('base.group_no_one'),
                }
                return result_preview
        except Exception as error:
            error.args += tuple(errors)
            # Due to lazy generators, UnicodeDecodeError (for
            # instance) may only be raised when serializing the
            # preview to a list in the return.
            _logger.debug("Error during parsing preview", exc_info=True)
            preview = None
            if self.file_type == 'text/csv':
                preview = self.file[:ERROR_PREVIEW_BYTES].decode('iso-8859-1')
            return {
                'error': str(error),
                # iso-8859-1 ensures decoding will always succeed,
                # even if it yields non-printable characters. This is
                # in case of UnicodeDecodeError (or csv.Error
                # compounded with UnicodeDecodeError)
                'preview': preview,
            }


    def _get_date_document(self, date_tmp):
        value = {}
        date_document = time.strftime('%Y-%m-%d', time.strptime(date_tmp, '%d/%m/%Y'))
        if 'withholding' in self.type_document:
            value['date_withholding'] = date_document
        elif 'transport' in self.type_document:
            value['date_emission'] = date_document
        else:
            value['date_invoice'] = date_document
        return value, date_document


    def _get_infoTributaria(self, infoTributaria):
        error = []
        property_account_position_id = False
        a_est = infoTributaria.get('estab', False)
        a_pun = infoTributaria.get('ptoEmi', False)
        code_doc = infoTributaria.get('codDoc', False)
        vals = {
            'firstname': infoTributaria.get('razonSocial', False),
            'name': infoTributaria.get('razonSocial', False),
            'street': infoTributaria.get('dirMatriz', False),
            'vat': infoTributaria.get('ruc', False),
        }
        if 'nombreComercial' in infoTributaria:
            vals['comercial_name'] = infoTributaria.get('nombreComercial', False)
        partner_id, type_doc_id, type_form = self._get_type_document(code_doc, vals)
        aut, error_aut = self._get_authorization(partner_id, a_est, a_pun, type_doc_id)
        error += error_aut
        vals = {
            'is_electronic': True,
            'environment': TYPE_ENVIRON[int(infoTributaria.get('ambiente', False))],
            'emission_code': infoTributaria.get('tipoEmision', False),
            'access_key': infoTributaria.get('claveAcceso', False),
            'authorization_number': infoTributaria.get('claveAcceso', False),
            'type_document_id': type_doc_id.id,
            'number': infoTributaria.get('secuencial', False),
            'internal_number': int(infoTributaria.get('secuencial', False)),
            'type': self.type_document,
            'name': '%s-%s-%s' % (a_est, a_pun, infoTributaria.get('secuencial', False)),
        }
        if len(aut) == 1:
            vals['authorization_id'] = aut.id
        if self.type_document in ['in_invoice', 'in_refund', 'in_withholding']:
            vals['partner_id'] = partner_id.id
            property_account_position_id = partner_id.property_account_position_id or False
        regimen = False
        if 'regimenMicroempresas' in infoTributaria:
            regimen = infoTributaria['regimenMicroempresas']
        elif 'contribuyenteRimpe' in infoTributaria:
            regimen = infoTributaria['contribuyenteRimpe']
        if regimen:
            property_account_position_id = self.env['account.fiscal.position'].search([('name','=',regimen), ('company_id','=',self.env.user.company_id.id)])
        if property_account_position_id:
            vals['fiscal_position_id'] = property_account_position_id.id or False
        _logger.info('OK Reading infoTributaria')
        return vals, error

    def _get_payments(self, infoContent, date_emission):
        lines = []
        lPayments = []
        if isinstance(infoContent['pagos']['pago'], dict):
            lPayments += [infoContent['pagos']['pago']]
        else:
            lPayments += infoContent['pagos']['pago']
        for line in lPayments:
            days = float(line['plazo']) if 'plazo' in line else 0
            date_due = fields.Date.from_string(date_emission) + relativedelta(days=days)
            lines.append((0, 0, {
                'method_id': self.env['account.method.payment'].search([('code','=',line['formaPago'])]).id,
                'days': days,
                'date_due': date_due,
                'value': 'fixed',
                'amount': line.get('total', 0.0),
                'currency_id': self.env.user.company_id.currency_id.id,
            }))
        return lines

    def _get_infoVoucher(self, infoContent, vals, type_doc):
        error = []
        partner_id = self.env['res.partner']
        company_id = self.env.user.company_id
        date_tmp = infoContent.get('fechaIniTransporte', False) if self.type_document == 'out_transport' else infoContent.get('fechaEmision', False)
        val_date, date_document = self._get_date_document(date_tmp)
        vals.update(val_date)
        if 'partner_id' in vals:
            partner_id = partner_id.browse(vals['partner_id'])
        if 'obligadoContabilidad' in infoContent:
            partner_id.write({'check_accounting': False if infoContent['obligadoContabilidad'] == 'NO' else True})
        if self.type_document in ['in_invoice']:
            #if company_id.vat != infoContent['identificacionComprador']:
            #    error.append(_('The document to be imported belongs to another company %s %s and cannot be imported.')
            #                    % (infoContent.get('razonSocialComprador'), infoContent.get('identificacionComprador')))
            if 'pagos' in infoContent:
                vals.update({'payment_method_ids': self._get_payments(infoContent, date_document)})
        if self.type_document in ['in_refund'] or type_doc=='notaDebito':
            ninvoice = infoContent.get('numDocModificado', False)
            ndate = infoContent.get('fechaEmisionDocSustento', False)
            inv_date = time.strftime('%Y-%m-%d', time.strptime(ndate, '%d/%m/%Y'))
            list_invoice = ninvoice.split('-')
            vals['tmpl_entity'] = list_invoice[0]
            vals['tmpl_emission'] = list_invoice[1]
            vals['tmpl_number'] = list_invoice[2]
            vals['tmpl_invoice_date'] = inv_date
            vals['reason'] = infoContent.get('motivo', False)
            invoice_id = self.env['account.invoice'].search([('name', '=', ninvoice),('company_id','=',company_id.id),('state','!=','draft')], limit=1)
            if invoice_id:
                vals['refund_invoice_id'] = invoice_id.id
        if self.type_document in ['out_invoice']:
            value = {
                'firstname': infoContent.get('razonSocialComprador', False),
                'name': infoContent.get('razonSocialComprador', False),
                'street': infoContent.get('direccionComprador', False),
                'vat': infoContent.get('identificacionComprador', False),
            }
            partner_id = self.env['res.partner']._get_info_partner(value, customer=True)
            vals['partner_id'] = partner_id.id
            if 'pagos' in infoContent:
                vals.update({'payment_method_ids': self._get_payments(infoContent, date_document)})
        if self.type_document in ['out_withholding']:
            value = {
                'firstname': infoContent.get('razonSocialSujetoRetenido', False),
                'name': infoContent.get('razonSocialSujetoRetenido', False),
                #'related_party': infoContent.get('parteRel', False),
                'vat': infoContent.get('identificacionSujetoRetenido', False),
                'check_accounting': False if infoContent['obligadoContabilidad'] == 'NO' else True
            }
            partner_id = self.env['res.partner']._get_info_partner(value, customer=True)
            vals['partner_id'] = partner_id.id
        if self.type_document in ['out_transport']:
            value = {
                'firstname': infoContent.get('razonSocialTransportista', False),
                'name': infoContent.get('razonSocialTransportista', False),
                'driver': True,
                'vat': infoContent.get('rucTransportista', False),
                'check_accounting': False if infoContent['obligadoContabilidad'] == 'NO' else True
                #'related_party': infoContent.get('parteRel', False), 
            }
            partner_id = self.env['res.partner']._get_info_partner(value, customer=False)
            vals['partner_id'] = partner_id.id
            vals['license_plate'] = infoContent.get('placa', False)
            vals['date_transport'] = self.fix_date(infoContent.get('fechaIniTransporte', False))
            vals['date_due'] = self.fix_date(infoContent.get('fechaFinTransporte', False))
            vals['address_starting'] = infoContent.get('dirPartida', False)
        _logger.info('OK Reading infoVoucher')
        return vals, error


    def _get_infoTax(self, infoLines, version):
        error = []
        list_details = []
        invoices = []       
        for tx in infoLines:
            if version == '2.0.0':
                for line in tx['retenciones']['retencion']:
                    infoD = dict()
                    tax, error_t, amount, add_discount = self._get_tax(line)
                    infoD.update(self._get_line(tax, line))
                    error += error_t
                    resInfo, inv, error_t = self._get_line_sustento(tx, version)
                    infoD.update(resInfo)
                    invoices += inv.ids
                    error += error_t
                    list_details.append((0, False, infoD))
            else:
                infoD = dict()
                tax, error_t, amount, add_discount = self._get_tax(tx)
                infoD.update(self._get_line(tax, tx))
                error += error_t
                resInfo, inv, errorT = self._get_line_sustento(tx, version)
                infoD.update(resInfo)
                invoices += inv.ids
                error += errorT
                list_details.append((0, False, infoD))
        _logger.info('OK Reading infoTax')
        return list_details, set(invoices), error


    def _get_withhold(self, detalles, version, vals):
        company = self.env.user.company_id
        infoD, invoices, error = self._get_infoTax(detalles, version)
        invoices = list(invoices)
        if len(invoices) == 1:
            inv = self.env['account.invoice'].browse(invoices[0])
            #vals['invoice_id'] = inv.id or False
            #vals['tmpl_invoice_date'] = inv.date_invoice or False
            vals['origin'] = inv.name or False
        elif len(invoices) > 1:
            invs = self.env['account.invoice'].browse(invoices)
            vals['multi_invoices'] = True
            vals['origin'] = ', '.join([inv.name for inv in invs])
        else:
            for line in infoD:
                retencion = line[2]
                invoices.append(retencion['tmpl_invoice_number'])
            #vals['multi_invoices'] = True
            vals['origin'] = ', '.join([inv for inv in invoices])
        vals['withholding_line_ids'] = infoD
        partner_id = self.env['res.partner'].browse(vals['partner_id'])
        if partner_id.property_account_receivable_id:
            vals['account_id'] = partner_id.property_account_receivable_id.id
        else:
            vals['account_id'] = company.property_account_receivable_id.id
        vals['journal_id'] = company.property_receivable_journal_id.id
        return vals, error


    def _get_tax(self, tx):
        _logger.info('OK Reading Impuestos')
        error = []
        tax_amount = 0.0
        discount = 0.0
        company = self.env.user.company_id
        tax = self.env['account.tax']
        try:
            code_tax = tx.get('codigo', False)
            ca = tx.get('codigoRetencion', False) if 'withholding' in self.type_document else tx.get('codigoPorcentaje', False)
            type_tax = TYPE_TAX[code_tax]
            if type_tax == 'iva' and int(ca) == 0:
                type_tax = 'iva0'
            elif type_tax == 'iva' and int(ca) in [7,8,9,10,1,11,2,3] and 'withholding' in self.type_document:
                type_tax = 'renta_iva'
            elif type_tax == 'iva':
                type_tax = PER_TAX_IVA[ca]
            if 'descuentoAdicional' in tx:
                discount += float(tx.get('descuentoAdicional', 0.0))
            tax_g = self.env['account.tax.group'].search([('type', '=', type_tax), ('code', '=', code_tax)])
            domain = [('tax_group_id', '=', tax_g.id), ('form_code_ats', '=', ca), ('company_id', '=', company.id),('active','=',True)]
            tax_id = self.env['account.tax'].with_context(type=self.type_document).search(domain, order='sequence ASC')
            if code_tax in ['3', '5'] and ca == '0':
                return (tax, error, tax_amount, discount)
            if len(tax_id) == 1:
                if tax_id.tax_adjustment:
                    tax_amount += float(tx.get('valor', 0.0))
                if tax_id:
                    tax = tax_id
            elif len(tax_id) > 1:
                por_re = 0.0
                if 'porcentajeRetener' in tx:
                    por_re = float(tx['porcentajeRetener'])
                elif 'tarifa' in tx:
                    por_re = float(tx['tarifa'])
                for t in tax_id:
                    if por_re == abs(t.amount) and not tax:
                        if tax.tax_adjustment:
                            tax_amount += float(tx.get('valor', 0.0))
                        tax = t
            else:
                error.append(_('Can not be found in tax %s %s base %s') % (ca, tax_g.name, tx.get('baseImponible', 0.0)))
            if not tax and len(tax_id) > 1:
                tax = tax_id[0]
            if tax and not tax.account_id:
                error.append(_('Not entered an account in the tax %s') % tax.name)
            if discount > 0:
                tax_amount += float(tx.get('valor', 0.0))
            return tax, error, tax_amount, discount
        except Exception as ex:
            _logger.error(_('Failed to read XML format from %s') % ex)
            return tax, error, tax_amount, discount


    def _get_infoDetails(self, infoContent, details, vals):
        company = self.env.user.company_id
        digit_pu = self.env['decimal.precision'].precision_get('Product Price')
        error = []
        list_detail = []
        sum_line_tmp = 0.0
        diffm = 1
        imTotal = float(infoContent.get('importeTotal', 0.0)) if 'invoice' in self.type_document else 0.0
        lDetails = []
        if isinstance(details['detalle'], dict):
            lDetails += [details['detalle']]
        else:
            lDetails += details['detalle']
        for dx in lDetails:
            sum_line_tmp += float(dx.get('precioTotalSinImpuesto', 0.0))
            lTaxes = []
            if isinstance(dx['impuestos']['impuesto'], dict):
                lTaxes += [dx['impuestos']['impuesto']]
            else:
                lTaxes += dx['impuestos']['impuesto']
            sum_line_tmp += sum(float(line['valor']) for line in lTaxes)
        if imTotal != sum_line_tmp and abs(imTotal - sum_line_tmp) <= 0.01 * (len(details) + len(infoContent.get('totalConImpuestos', []))):
            diffm = imTotal/(imTotal+(sum_line_tmp-imTotal)/2)
        for dx in lDetails:
            vals_line = {'type_discount': 'fixed'}
            code_main = dx.get('codigoInterno', False) if self.type_document in ['in_refund','out_refund'] else dx.get('codigoPrincipal', False)
            code_sec = dx.get('codigoAdicional', False) if self.type_document in ['in_refund','out_refund'] else dx.get('codigoAuxiliar', False)
            if code_main or code_sec:
                if code_main:
                    domain = ['|', '|', ('name','=',code_main), ('default_code','=',code_main), ('barcode','=',code_main)]
                if code_sec:
                    domain = ['|', '|', ('name','=',code_sec), ('default_code','=',code_sec), ('barcode','=',code_sec)]
                product_id = self.env['product.product'].search(domain, limit=1)
            vals_line['name'] = dx.get('descripcion', False)
            qty_tmp = float(dx.get('cantidad', 0))
            price_tmp = float(dx.get('precioUnitario', 0.0))
            discount = 0.0
            if 'descuento' in dx:
                discount = float(dx.get('descuento', 0.0))
            total_tmp = float(dx.get('precioTotalSinImpuesto', 0.0))
            if diffm != 1:
                total_tmp = max(total_tmp - 0.005, round(total_tmp * diffm, digit_pu)) if diffm < 1 else min(total_tmp + 0.0049, round(total_tmp * diffm, digit_pu))
            subtotal_tmp = price_tmp * qty_tmp
            #if discount > 0.0:
            #    discount = subtotal_tmp - total_tmp
            #    discount = discount * 100.0/price_tmp/qty_tmp
            if discount == 0.0 and subtotal_tmp != total_tmp:
                price_tmp = round(total_tmp/qty_tmp, digit_pu)
            
            vals_line['quantity'] = qty_tmp
            vals_line['price_unit'] = price_tmp
            vals_line['discount'] = discount

            taxes = self.env['account.tax']
            lTaxes = []
            if isinstance(dx['impuestos']['impuesto'], dict):
                lTaxes += [dx['impuestos']['impuesto']]
            else:
                lTaxes += dx['impuestos']['impuesto']
            for tx in lTaxes:
                tax, error_t, amount, add_discount = self._get_tax(tx)
                if tax: taxes |= tax
                error += error_t
            #if 'fiscal_position_id' in vals:
            #    fpos = self.env['account.fiscal.position'].browse(vals['fiscal_position_id'])
            #    taxes += fpos.map_not_tax().ids
                
            account_id = False
            if product_id:
                vals_line['product_id'] = product_id.id
                account_id = product_id.property_account_income_id if self.type_document in ['out_invoice'] else product_id.property_account_expense_id
            else:
                partner_id = self.env['res.partner'].browse(vals['partner_id'])
                if self.type_document in ['out_invoice']:
                    account_id = partner_id and partner_id.account_income_id or company.property_account_income_id 
                else:
                    account_id = partner_id and partner_id.account_expense_id or company.property_account_expense_id
            if len(account_id.tax_ids):
                taxes += account_id.tax_ids#fpos.map_tax(account_id.tax_ids).ids
            vals_line['account_id'] = account_id and account_id.id
            vals_line['invoice_line_tax_ids'] = [(6, 0, list(set(taxes.ids)))]
            vals_line['tax_tag_ids'] = [(6, 0, list(set(taxes.mapped('tag_ids').ids)))]
            if not account_id:
                error += [_('The default accounts are not entered in configurations or in product')]
            list_detail.append((0, False, vals_line))
        vals.update({'invoice_line_ids': list_detail})
        _logger.info(_('OK Reading details'))
        return vals, error


    def _get_infoReasons(self, infoContent, details, vals, taxes):
        company_id = self.env.user.company_id
        error = []
        list_detail = []
        lDetails = []
        if isinstance(details['motivo'], dict):
            lDetails += [details['motivo']]
        else:
            lDetails += details['motivo']
        for dx in lDetails:
            vals_line = {
                'name': dx.get('razon', False),
                'account_id': company_id.property_account_expense_id.id or False,
                'quantity': 1,
                'price_unit': dx.get('valor', False),
                'invoice_line_tax_ids': [(6, 0, list(set(taxes.ids)))],
                'tax_tag_ids': [(6, 0, list(set(taxes.mapped('tag_ids').ids)))],
            }
            list_detail.append((0, False, vals_line))
        vals.update({'invoice_line_ids': list_detail})
        _logger.info(_('OK Reading details'))
        return vals, error

    def _get_invoice(self, infoContent, vals, type_doc):
        error = []
        extra_val = {}
        company = self.env.user.company_id
        taxes_id = self.env['account.tax']
        partner_id = self.env['res.partner'].browse(vals['partner_id'])
        vals['document_type'] = 'refund' if 'refund' in self.type_document else 'invoice'
        if self.type_document in ['out_invoice']:
            vals['account_id'] = company.property_account_receivable_id.id
            vals['journal_id'] = company.property_receivable_journal_id.id
        else:
            vals['account_id'] = company.property_account_payable_id.id
            vals['journal_id'] = company.property_payable_journal_id.id
        vals['tax_support_id'] = self.env['account.tax.support'].search([('code', '=', '01')]).id
        if not vals.get('account_id'):
            if partner_id:
                vals['account_id'] = partner_id.property_account_receivable_id.id if self.type_document in ['out_invoice'] else partner_id.property_account_payable_id.id
                if not vals.get('account_id'):
                    error += [_('The default accounts are not entered in configurations or in supplier/customer')]
            else:
                error += [_('The default accounts are not entered in configurations or in supplier/customer')]
        if not vals.get('journal_id'):
            error += [_('Journal is not entered by default in configurations')]
        
        add_discount = 0.0
        discount_add = 0.0
        lTaxes = []
        if type_doc=='notaDebito':
            vals['document_type'] = 'debit'
            if isinstance(infoContent['impuestos']['impuesto'], dict):
                lTaxes += [infoContent['impuestos']['impuesto']]
            else:
                lTaxes += infoContent['impuestos']['impuesto']
        else:
            if isinstance(infoContent['totalConImpuestos']['totalImpuesto'], dict):
                lTaxes += [infoContent['totalConImpuestos']['totalImpuesto']]
            else:
                lTaxes += infoContent['totalConImpuestos']['totalImpuesto']
        
        for tx in lTaxes:
            tax, error_t, amount_manual, discount = self._get_tax(tx)
            discount_add += discount
            if tax:
                if amount_manual > 0.0 and add_discount == 0.0:
                    extra_val[tax.id] = {'manual': tax.tax_adjustment, 'amount': amount_manual, 'amount_tax': tax.amount}
                if add_discount > 0:
                    extra_val[tax.id] = {'manual': True, 'amount': amount_manual}
                if len(extra_val):
                    vals.update({'extra': extra_val})
                taxes_id |= tax
            error += error_t
        vals.update({'discount': discount_add})
        return vals, taxes_id, error


    def _get_information_adicional(self, infoAdicional):
        listAdicional = []
        lAdd = []
        if isinstance(infoAdicional['campoAdicional'], dict):
            lAdd += [infoAdicional['campoAdicional']]
        else:
            lAdd += infoAdicional['campoAdicional']
        for line in lAdd:
            if '#text' in line and '@nombre' in line:
                listAdicional.append((0, False, {
                    'name': line['@nombre'],
                    'value_tag': line['#text'],
                }))
        return listAdicional


    def _get_line(self, tax_id, line):
        info_line = {
            'name': tax_id.tax_group_id.type,
            'tax_id': tax_id.id,
            'account_id': tax_id.account_id and tax_id.account_id.id or False,
            'amount_base': float(line.get('baseImponible', 0.0)),
            'amount_tax': tax_id.amount,
            'amount': float(line.get('valorRetenido', 0.0))
        }
        return info_line


    def _get_review_xml(self, xml_data):
        context_comp = False
        content_json = dict()
        error_global = []
        version = '0.0.0'
        vals = {'authorization': True, 'received': True}
        type_doc, type_content = TYPE_MOVE[self.type_document]
        header_xml = xmltodict.parse(xml_data)
        header_json = json.loads(json.dumps(header_xml))
        if 'autorizacion' in header_json:
            header = header_json['autorizacion']
            vals.update({
                'message_state': header.get('estado', 'AUTORIZADO'),
                'authorization_number': header.get('numeroAutorizacion', False),
                'authorization_date': header.get('fechaAutorizacion', False),
                'environment': header.get('ambiente', 'PRODUCCIÓN'),
            })
            if 'authorization_date' in vals:
                try:
                    if 'AM' in vals['authorization_date']:
                        date_auth = datetime.datetime.strptime(vals['authorization_date'], '%m/%d/%Y %I:%M:%S %p')
                    elif 'PM' in vals['authorization_date']:
                        date_auth = datetime.datetime.strptime(vals['authorization_date'], '%m/%d/%Y %I:%M:%S %p')
                    elif '05:00' in vals['authorization_date']:
                        date_auth = datetime.datetime.strptime(vals['authorization_date'], '%Y-%m-%dT%H:%M:%S-05:00')
                    else:
                        date_auth = datetime.datetime.strptime(vals['authorization_date'], '%d/%m/%Y %H:%M:%S')
                    vals['authorization_date'] = date_auth.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                except Exception as er:
                    _logger.error(_('Cannot read date format in XML %s: %s') % (vals['authorization_date'], er))
            if 'comprobante' in header_json['autorizacion']:
                context_comp = header_json['autorizacion']['comprobante']
                content_xml = xmltodict.parse(context_comp)
                content_json = json.loads(json.dumps(content_xml))
        if 'notaDebito' in content_json:
            type_doc, type_content = TYPE_MOVE['in_debit']
        if type_doc in content_json:
            version = content_json[type_doc]['@version']
            if 'infoTributaria' in content_json[type_doc]:
                infoTributaria = content_json[type_doc]['infoTributaria']
                data, error = self._get_infoTributaria(infoTributaria)
                vals.update(data)
                error_global += error
            if 'info'+type_content in content_json[type_doc]:
                infoContent = content_json[type_doc]['info'+type_content]
                vals, error = self._get_infoVoucher(infoContent, vals, type_doc)
                error_global += error
                if 'invoice' in self.type_document or 'refund' in self.type_document:
                    vals, taxes_id, error = self._get_invoice(infoContent, vals, type_doc)
                    error_global += error
                    type_detail = 'motivos' if type_doc=='notaDebito' else 'detalles'
                    details = content_json[type_doc][type_detail]
                    if type_detail=='motivos':
                        vals, error = self._get_infoReasons(infoContent, details, vals, taxes_id)
                    else:
                        vals, error = self._get_infoDetails(infoContent, details, vals)
                    error_global += error
                elif 'withholding' in self.type_document:
                    if version == '2.0.0':
                        detalles = content_json[type_doc]['docsSustento']['docSustento']
                    else:
                        detalles = content_json[type_doc]['impuestos']['impuesto']
                    lDetails = []
                    if isinstance(detalles, dict):
                        lDetails += [detalles]
                    else:
                        lDetails += detalles
                    vals, error = self._get_withhold(lDetails, version, vals)
                    error_global += error
            if 'infoAdicional' in content_json[type_doc]:
                infoAdicional = content_json[type_doc]['infoAdicional']
                data = self._get_information_adicional(infoAdicional)
                vals.update({'line_info_ids': data})
        vals.update({'edi_document_ids': [(0, False, {
            'message': '%s en la base del SRI' % vals['message_state'],
            'add_information': vals['access_key'],
            'type': vals['message_state'],
            'date_action': vals['authorization_date']}
            )]
        })
        #if self.type_document == 'out_transport':
        #    rresult, transports, error = self._get_contents_xml(context_comp)
        #    error_global += error
        _logger.info('OK Reading XML')
        return vals, error_global


    def _search_sri(self, access_key, path):
        try:
            path = '%s%s' % (path, access_key+'.xml')
            if not os.path.exists(path):
                env = access_key[23]
                SriService.set_active_env(int(env))
                url_ws = SriService.get_active_ws()[1]
                client = zeep.Client(wsdl=url_ws)
                result = client.service.autorizacionComprobante(access_key)
                if int(result.numeroComprobantes) > 0:
                    rautorizacion = result.autorizaciones.autorizacion[0]
                    xml_data = self.render_authorized_edocument(rautorizacion)
                    file_signed = open(path, 'w')
                    file_signed.write(xml_data)
                    file_signed.close()
        except Exception as ex:
            _logger.error(_('Unable to read document in SRI. %s') % str(ex))


    def render_authorized_edocument(self, autorizacion):
        tmpl_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'src', 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        auth_xml = {
            'estado': autorizacion.estado,
            'numeroAutorizacion': autorizacion.numeroAutorizacion if autorizacion.numeroAutorizacion is not None else False,
            'fechaAutorizacion': str(autorizacion.fechaAutorizacion.strftime("%d/%m/%Y %H:%M:%S")),
            'ambiente': autorizacion.ambiente,
            'comprobante': autorizacion.comprobante
        }
        if autorizacion.estado == 'AUTORIZADO':
            edocument_tmpl = env.get_template('authorized_document.xml')
        if not autorizacion.estado == 'AUTORIZADO':
            edocument_tmpl = env.get_template('not_authorized_document.xml')
            messages = []
            if autorizacion.mensajes is not None:
                mensajes = autorizacion.mensajes.mensaje
                if mensajes is not None:
                    for m in mensajes:
                        mensaje = {
                            'identificador': m.identificador,
                            'mensaje': m.mensaje+': '+m.informacionAdicional,
                            'tipo': m.tipo
                        }
                        messages.append(mensaje)
            auth_xml.update({'mensajes': messages})
        return edocument_tmpl.render(auth_xml)


    def _get_contents_xml(self, contents_xml):
        row = {}
        error = []
        transports = []
        infoD, invoices, errorD = self._get_infoDesti(contents_xml)
        row.update(infoD)
        obj_trans = self.env['transport.permit']
        for inv in invoices:
            type_document = self.env['account.type.document'].search([('code', '=', '06')], limit=1).id
            vals = {'type_document_id': type_document,
                    'type': 'out_transport',
                    'tmpl_entity': inv.authorization_id.entity,
                    'tmpl_emission': inv.authorization_id.issue,
                    'tmpl_number': inv.number,
                    'tmpl_invoice_date': inv.date_invoice,
                    'invoice_origin_id': inv.id,
                    'addressee_id': inv.partner_id.id,
                    'origin': inv.name,
                    'transport_permit_line_ids': obj_trans._get_details(inv.invoice_line_ids)
            }
            vals.update(row)
            trans = obj_trans.create(vals)
            transports.append(trans)
            _logger.info('Generate Transport %s' % trans.id)
            trans._cr.commit()
        error += errorD
        return (row, transports, error)


    def _get_type_document(self, code_doc, vals):
        company = self.env.user.company_id
        partner_id = self.env['res.partner']._get_info_partner(vals)
        type_form = 'external'
        if 'out' in self.type_document:
            code = 18
            if self.type_document == 'out_refund':
                code = '04'
            elif self.type_document == 'out_transport':
                code = '06'
            elif self.type_document == 'out_withholding':
                code = '07'
            type_doc_id = self.env['account.type.document'].search([('code', '=', code)])
            partner_id = company.partner_id
            type_form = 'internal'
        else:
            type_doc_id = self.env['account.type.document'].search([('code', '=', code_doc)])
        return partner_id, type_doc_id, type_form
    

    def _get_authorization(self, partner_id, entity, issue, type_doc_id):
        obj_authorization = self.env['account.authorization']
        #establishment_id = self.env.user.establishment_id or False
        type_doc = 'internal' if self.type_document in ['out_invoice', 'out_withholding'] else 'external'
        aut = obj_authorization._find(entity, issue, type_doc_id.code, True, partner_id, type_doc) #establishment_id
        error = list()
        if len(aut) > 1:
            error += [_('There are several authorizations with the establishment %s and emission point %s of %s') % (entity, issue, partner_id.name)]
        vals = {
            'name': 'AE%s%s%s' % (type_doc_id.code, entity, issue),
            'partner_id': partner_id.id,
            'entity': entity,
            'issue': issue,
            'is_electronic': True,
            'type_document_id': type_doc_id.id,
            'type': type_doc,
            'manual_sequence': True,
            'number_since': 1,
            'number_to': 999999999,
        }
        if not aut and 'out' not in self.type_document:
            #if establishment_id:
            #    values['establishment_id'] = establishment_id.id
            aut = obj_authorization.create(vals)
        else:
            aut.write(vals)
        return aut, error


    def _get_line_sustento(self, line, version):
        error = []
        infod = dict()
        path = '/tmp/%s/' % self._cr.dbname
        obj_invoice = self.env['account.invoice']
        typex = 'out_invoice' if self.type_document == 'in_withholding' else 'in_invoice'
        inv = self.env['account.invoice']
        type_document_id = self.env['account.type.document'].search([('code', '=', line.get('codDocSustento', False) or '01')])
        if 'numDocSustento' in line:
            line_number = line.get('numDocSustento', False)
            line_date =self.fix_date(line.get('fechaEmisionDocSustento', False))
            number_tmp = re.sub(r'^(\d{3})(\d{3})(\d{9})$', r'\1-\2-\3', line_number)
            inv = inv.search([('type', '=', typex), ('name', '=', number_tmp),
                ('company_id', '=', self.env.user.company_id.id)], limit=1)
            livelihood_id = type_document_id
            if version == '2.0.0' and not inv:
                if 'numAutDocSustento' in line:
                    access_key = line.get('numAutDocSustento', False)
                    inv = obj_invoice.search([('authorization_number', '=', access_key), ('company_id', '=', self.env.user.company_id.id)])
                    if not inv:
                        self._search_sri(access_key, path)
                        xml_data = self._exists_xml(access_key)
                        if xml_data:
                            vals, error = self._get_review_xml(xml_data)
                            if len(vals):
                                vals['type'] = typex
                                inv = obj_invoice.create(vals)
                                _logger.info(_('Done invoice'))
                        
            if inv:
                number_tmp = inv.name
                line_date = inv.date_invoice
                livelihood_id = inv.type_document_id
                infod.update({'invoice_id': inv.id})
        else:
            number_tmp = '000-000-000000000'
            line_date = fields.Date.today()
            livelihood_id = type_document_id
            _logger.info(_('You do not have a related document.'))
        if 'fechaEmisionDocSustento' in line:
            line_date = line['fechaEmisionDocSustento']
        infod.update({
            'tmpl_invoice_number': number_tmp,
            'tmpl_invoice_date': time.strftime('%Y-%m-%d', time.strptime(line_date, '%d/%m/%Y')),
            'livelihood_id': livelihood_id.id,
        })
        return infod, inv, error


    def _get_infoDesti(self, contents_xml):
        error = []
        invoices = []
        info_des = {}
        details = contents_xml.get('destinatarios')
        model = self.env['account.invoice'].with_context(import_file=True)
        for dx in details:
            num_aut = dx.get('numAutDocSustento', False)
            doc_id = model.search([('authorization_number', '=', num_aut), ('company_id', '=', self.env.user.company_id.id)])
            if doc_id:
                if doc_id not in invoices:
                    invoices.append(doc_id)
            else:
                error += [_('No existe la factura %s para la Guía') % dx.get('numDocSustento', False)]
            info_des.update({
                'route': dx.get('ruta', False)
            })
        return (info_des, invoices, error)


    def fix_date(self, date):
        d = time.strftime('%Y-%m-%d', time.strptime(date, '%d/%m/%Y'))
        return d


    def _exists_xml(self, access_key):
        xml_data = False
        path = '/tmp/%s/%s' % (self._cr.dbname, access_key+'.xml')
        if os.path.exists(path):
            file_signed = open(path, 'r')
            xml_data = file_signed.read()
            file_signed.close()
        return xml_data


    @api.multi
    def _parse_import_data(self, data, import_fields, options):
        if self.file_type not in ['text/xml', 'text/plain']:
            return super(Import, self)._parse_import_data(data, import_fields, options)
        else:
            datas = []
            errors = []
            if self.file_type == 'text/xml':
                xml_data = self.file.decode('utf-8')
                vals, error = self._get_review_xml(xml_data)
                datas += [vals]
                errors += list(set(error))
            else:
                index = import_fields.index('authorization_number')
                rows = [row for row in data if row[0] in ['NOT JOINED', 'NO INGRESADO']]
                for record in rows:
                    access_key = record[index]
                    xml_data = self._exists_xml(access_key)
                    if xml_data:
                        vals, error = self._get_review_xml(xml_data)
                        datas += [vals]
                        errors += list(set(error))
            return datas, errors


    def do(self, fields, options, dryrun=False):
        ids = []
        messages = []
        if self.file_type not in ['text/xml', 'text/plain']:
            return super(Import, self).do(fields, options, dryrun)
        else:
            self.ensure_one()
            self._cr.execute('SAVEPOINT import')
            options['headers'] = False
            try:
                data, import_fields = self._convert_import_data(fields, options)
                # Parse date and float field
                data, errors = self._parse_import_data(data, import_fields, options)
                if len(errors):
                    return [{
                        'type': 'error',
                        'message': ','.join(errors),
                        'record': False,
                    }]
            except ValueError as error:
                return [{
                    'type': 'error',
                    'message': pycompat.text_type(error),
                    'record': False,
                }]

            _logger.info('importing %d rows...', len(data))
    
            model = self.env[self.res_model].with_context(import_file=True)
            defer_parent_store = self.env.context.get('defer_parent_store_computation', True)
            if defer_parent_store and model._parent_store:
                model = model.with_context(defer_parent_store_computation=True)
            import_result = {'ids': ids, 'messages': messages}
            for vals in data:
                if 'extra' in vals:
                    vals.update(vals['extra'])
                    del vals['extra']
                new_record = model.search([('access_key','=',vals['access_key'])])
                if not new_record:
                    new_record = model.create(vals)
                if new_record: ids.append(new_record.id)
                import_result['ids']= ids
            _logger.info('done')
    
            # If transaction aborted, RELEASE SAVEPOINT is going to raise
            # an InternalError (ROLLBACK should work, maybe). Ignore that.
            # TODO: to handle multiple errors, create savepoint around
            #       write and release it in case of write error (after
            #       adding error to errors array) => can keep on trying to
            #       import stuff, and rollback at the end if there is any
            #       error in the results.
            try:
                if dryrun:
                    self._cr.execute('ROLLBACK TO SAVEPOINT import')
                else:
                    self._cr.execute('RELEASE SAVEPOINT import')
            except psycopg2.InternalError:
                pass
    
            return import_result['messages']


    def _value_document(self, access_key, record):
        error = list()
        number = record[1].split('-')
        code_doc = access_key[8:10]
        a_est = number[0]
        a_pun = number[1]
        number = number[2]
        environ = int(access_key[23])
        value_partner = {
            'firstname': record[3],
            'name': record[3],
            'vat': record[2],
        }
        partner_id, type_doc_id, type_form = self._get_type_document(code_doc, value_partner)
        aut, error_aut = self._get_authorization(partner_id, a_est, a_pun, type_doc_id, type_form)
        error += error_aut
        date_auth = record[5]
        value = {
            'is_electronic': True,
            'environment': TYPE_ENVIRON[environ],
            'emission_code': 1,
            'access_key': record[9],
            'authorization_number': record[9],
            'message_state': 'AUTORIZADO',
            'received': True,
            'authorization': True,
            'authorization_date': date_auth,
            'type_document_id': type_doc_id.id,
            'authorization_id': aut.id,
            'number': number,
            'internal_number': int(number),
            'type': self.type_document,
            'name': record[1],
            'partner_id': partner_id.id,
        }
        val_date, date_document = self._get_date_document(record[4])
        value.update(val_date)
        value.update(self._add_record(record))
        return value, error


    def _add_record(self, record):
        account_tax = self.env['account.tax'].sudo()
        ir_default = self.env['ir.default'].sudo()
        amount = float(record[10])
        company = self.env.user.company_id
        default_sale_tax_id = account_tax.browse(ir_default.get('product.template', 'taxes_id', company_id=company.id) or [])
        default_purchase_tax_id = account_tax.browse(ir_default.get('product.template', 'supplier_taxes_id', company_id=company.id) or [])
        tax = default_sale_tax_id if 'out' in self.type_document else default_purchase_tax_id
        account = company.property_account_income_id.id if 'out' in self.type_document else company.property_account_expense_id.id
        percen = (tax.amount/100)+1
        amount_price = round(amount/percen, 4)
        lines = [(0, False, {
            'name': _('Done Sale') if 'out' in self.type_document else _('Done Purchase') ,
            'quantity': 1,
            'invoice_line_tax_ids': [(6, 0, [tax.id])],
            'account_id': account,
            'price_unit': round(amount_price, 4),
        })]
        return {'invoice_line_ids': lines}

    def _review_document(self, model, data):
        _logger.info('%s: %s of list %s' % (self.res_model, self.type_document, data))
        import_result = {'ids': [], 'messages': []}
        list_data = []
        for xauth in data:
            dict_data, error = self._search_sri(xauth)
            if len(error) == 0:
                val_extra = dict()
                if self.type_document != 'out_transport':
                    if 'extra' in dict_data:
                        val_extra.update(dict_data['extra'])
                        del dict_data['extra']
                    object_ids = model.create(dict_data)
                    object_ids._cr.commit()
                    if 'invoice' in self.type_document:
                        object_ids._settings_data(val_extra)
                doc_id = model.search([('type', '=', self.type_document), ('authorization_number', '=', dict_data['authorization_number']), ('company_id', '=', self.env.user.company_id.id)])
                if doc_id:
                    import_result['ids'] += [rec.id for rec in doc_id]
                else:
                    list_data.append(dict_data)
            else:
                _logger.info(', '.join(error))
                return [{
                    'type': 'error',
                    'message': pycompat.text_type(', '.join(error)),
                    'record': False,
                }]

        if len(list_data):
            for ldata in list_data:
                if ldata:
                    object_ids = model.search([('type', '=', self.type_document), ('authorization_number', '=', ldata['authorization_number']), ('company_id', '=', self.env.user.company_id.id)])
                    if not object_ids:
                        if self.type_document != 'out_transport':
                            object_ids = model.create(ldata)
                            object_ids._cr.commit()
                    import_result['ids'] += [x.id for x in object_ids]
                    _logger.info('done')
        return import_result
