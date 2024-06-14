# -*- coding: utf-8 -*-

import base64
import io
import logging

from barcode import generate

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round as round

from . import utils


MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.depends('transport_permit_ids', 'transport_permit_ids.state')
    def _get_document_count(self):
        super(AccountInvoice, self)._get_document_count()
        for invoice in self:
            transport_line_ids = self.env['transport.permit.line'].search([('invoice_id', '=', invoice.id)]) 
            invoice.update({
                'transport_count': len(transport_line_ids.mapped('transport_permit_id').ids)
            })

    substitute_permit = fields.Boolean(string='Transport Permit Substitute', copy=True,
        help='Enable this option, indicates that the invoice replaces the referral guide')
    edi_document_ids = fields.One2many('account.edi.document', 'invoice_id', string='History')
    transport_count = fields.Integer(string='Transport Count', compute='_get_document_count', readonly=True)
    transport_permit_ids = fields.One2many('transport.permit', 'invoice_id', string='Transport Permits', copy=True)
    batch_id = fields.Many2one('account.edi.document.batch', string='Batch', copy=False)

    @api.onchange('authorization', 'received', 'access_key')
    def _onchange_historys(self):
        list_code = []
        res = {'value': {'received': False, 'authorization': False, 'message_state': 'ENVIAR'}}
        codes = self.env['code.validation.document'].search([])
        list_code += [x.code for x in codes]
        for line_id in sorted(self.edi_document_ids, key=lambda x: x.id, reverse=False):
            res['value']['message_state'] = line_id.type
            if line_id.type == 'RECIBIDA':
                res['value']['received'] = True
            if line_id.type == 'AUTORIZADO':
                res['value']['authorization'] = True
        return res

    def _get_line_specific_history(self, action):
        line = self.env['account.edi.document']
        if len(self.edi_document_ids) > 0:
            domain = [('id', 'in', self.edi_document_ids.ids), ('type', '=', action)]
            line = line.search(domain, limit=1, order='id desc')
        return line
    
    @api.onchange('transport_permit_ids')
    def _onchange_transport_permit_ids(self):
        if len(self.transport_permit_ids) > 1:
            raise UserError(_('Only one transport permit can be added for each Invoice'))

    @api.multi
    def action_restore_doc(self):
        self.ensure_one()
        self._validate_invoice()

    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None, form=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id, form=form)
        values['partner_invoice_id'] = invoice.partner_invoice_id and invoice.partner_invoice_id.id or False
        # if invoice.substitute_permit:
        #    values['substitute_permit']= True
        #    values['transport_permit_ids']= self._refund_cleanup_transport_lines(invoice.transport_permit_ids)
        return values

    @api.model
    def _refund_cleanup_transport_lines(self, lines):
        """ Convert records to dict of values suitable for one2many line creation

            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.items():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    if name == 'invoice_id':
                        values[name] = False
                    else:
                        values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'transport_permit_line_ids':
                    values[name] = self._refund_cleanup_transport_lines(line.transport_permit_line_ids)
                if name == 'state':
                    values[name] = 'draft'
            result.append((0, 0, values))
        return result

    @api.model
    def automatic_sent_to_sri(self, sent_mail=False, sent_sri=False):
        cron = self._context.get('cron', False)
        domain = [('state', 'in', ['open', 'paid']), ('type', 'in', ['out_invoice', 'out_refund']), ('is_electronic', '=', True)]
        if sent_mail:
            i = 0
            domain_mail = domain + [('authorization', '=', True), ('sent', '=', False), ('partner_id', '!=', self.env.ref('oe_base.final_consumer').id)]
            invoices = self.search(domain_mail, limit=30, order='id ASC')
            max_doc = len(invoices)
            for invoice in invoices:
                i += 1
                invoice._send_mail()
                _logger.info(_('Send document %s by mail %s of %s') % (invoice.name, i, max_doc))
        if sent_sri:
            i = 0
            invoices = self.search(domain + [('received', '=', False)], limit=50, order='id ASC')
            max_doc = len(invoices)
            for invoice in invoices:
                i += 1
                if len(invoice.edi_document_ids) >= 2:
                    msg = _("""You have exceeded the number of attempts allowed per day 3 in the SRI.
                        Check the incidents that have occurred in the SRI Information. %s of %s""") % (invoice.type_document_id.name, invoice.name)
                    _logger.critical(msg)
                    if not cron: raise UserError(msg)
                else:
                    invoice.action_send_to_sri()
                    _logger.info(_('Send of documento %s SRI %s of %s') % (invoice.name, i, max_doc))

    def _send_mail(self):
        context, compose_form = self._action_invoice_sent()
        composer = self.env['mail.compose.message'].with_context(context).create({'composition_mode': 'comment'})
        template_id = context['default_template_id']
        if template_id:
            update_values = composer.onchange_template_id(template_id, 'comment', self._name, self.id)['value']
            composer.write(update_values)
        composer.send_mail()

    def _create_fist_history(self):
        if not len(self.edi_document_ids):
            vals = {
                'sequence': 10,
                'code': 0,
                'invoice_id': self.id,
                'type': 'ENVIAR',
                'add_information': self.access_key,
            }
            self.env['account.edi.document'].create(vals)

    @api.multi
    def action_invoice_open(self):
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.substitute_permit and not len(inv.transport_permit_ids)):
            raise UserError(_('Enter data from the Substitute Remission Guide in the invoice'))
        res = super(AccountInvoice, self).action_invoice_open()
        to_open_invoices.filtered(lambda inv: inv.is_electronic)._create_fist_history()
        for inv in self.filtered(lambda i: i.substitute_permit):
            inv.transport_permit_ids.write({
                'date_emission': inv.date_invoice,
                'number': inv.number,
                'internal_number': inv.internal_number,
                'name': inv.name,
            })
            inv.transport_permit_ids.action_transport_approved()
        return res

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
        vals = self._onchange_historys()
        self.write(vals['value'])

    def render_document(self):
        data = {}
        data.update(utils._info_tributary(self))
        data.update(self._info_invoice())
        data.update({'claveAcceso': self.access_key})
        details = self._details()
        data.update(details)
        if self.is_refund:
            data.update(self._refunds())
        if self.type_document_id.code != '05':
            data.update(self._compute_discount(details))
        if self.substitute_permit:
            data.update(self._destinations())
        data.update(self._infoAdicional())
        doc_tmpl = utils._get_type_document(self.type_document_id.code)
        return doc_tmpl.render(data)

    def _info_invoice(self):
        opurchase = True if self.type_document_id.code == '03' else False
        company = self.company_id
        partner = self.partner_id
        if not partner.l10n_latam_identification_type_id: raise UserError(_('The customer is not validated correctly'))
        addressp = utils.fix_chars(partner._display_address())
        type_partner = 'Proveedor' if opurchase else 'Comprador'
        infoFactura = {
            'fechaEmision': utils.fix_date(self.date_invoice),
            'obligadoContabilidad': 'SI' if company.partner_id.check_accounting else 'NO',
            'tipoIdentificacion' + type_partner: partner.l10n_latam_identification_type_id.code,
            'razonSocial' + type_partner: utils.fix_chars(partner.name),
            'identificacion' + type_partner: partner.vat,
            'direccion' + type_partner: utils.fix_chars(addressp),
            'totalSinImpuestos': '%.2f' % (self.amount_subtotal),
            'pagos': self._get_payment_shape(),
        }
                        
        establ = self.authorization_id.establishment_id
        if establ:
            dirEstablecimiento = utils.fix_chars(establ._display_address())
            infoFactura.update({'dirEstablecimiento': dirEstablecimiento})
        
        if 'invoice' in self.type:
            if not opurchase:
                infoFactura.update({
                    'totalDescuento': '%.2f' % (round(self.amount_discount, 4)),
                    'propina': '0.00',
                })
            infoFactura.update({
                'importeTotal': '{:.2f}'.format(self.total),
                'moneda': 'DOLAR',
            })
        
        if self.withholding_id:
            infoFactura['valorRetIva'] = '{:.2f}'.format(abs(self.withholding_id.amount_iva) or 0.0)
            infoFactura['valorRetRenta'] = '{:.2f}'.format(abs(self.withholding_id.amount_renta) or 0.0)
        
        if company.company_registry:
            infoFactura.update({'contribuyenteEspecial': company.company_registry})
        
        if self.type == 'out_refund':
            inv = self.browse(self.refund_invoice_id.id) if self.refund_invoice_id.id else False
            notacredito = {
                'codDocModificado': inv.type_document_id.code if inv else '01',
                'numDocModificado': inv.name if inv else self.origin,
                'fechaEmisionDocSustento': utils.fix_date(inv.date_invoice) if inv else utils.fix_date(self.tmpl_invoice_date)
            }
            if self.type_document_id.code == '04':
                notacredito['motivo'] = utils.fix_chars(self.reason)
                notacredito['valorModificacion'] = '%.2f' % self.total
            infoFactura.update(notacredito)
        
        infoFactura.update({'totalConImpuestos': self._taxes(self.tax_line_ids)})
        if self.type == 'out_refund' and self.type_document_id.code == '05':
            infoFactura.update({'valorTotal': '%.2f' % self.total})
        
        return infoFactura

    def _taxes(self, tax_line_ids):
        total_with_taxs = []
        for tax in tax_line_ids:
            if tax.tax_id.tax_group_id.type in ['iva', 'iva0', 'ice', 'exiva', 'nobiva']:
                codePor = utils.codeTax[str(int(tax.tax_id.amount))] if tax.tax_id.tax_group_id.type == 'iva' else tax.tax_id.form_code_ats
                vals = {
                    'codigo': tax.tax_id.tax_group_id.code,
                    'codigoPorcentaje': codePor,
                    'baseImponible': '{:.2f}'.format(tax.base),
                    'tarifa': int(tax.tax_id.amount),
                    'valor': '{:.2f}'.format(tax.amount)
                }
                if tax.tax_id.tax_group_id.type == 'iva':
                    vals['descuentoAdicional'] = self.discount
                total_with_taxs.append(vals)
        return total_with_taxs

    def _details(self):
        details = []
        for line in self.invoice_line_ids:
            if self.type_document_id.code == '05':
                detail = {
                    'razon': utils.fix_chars(line.name.strip()),
                    'valor': '%.4f' % (line.price_subtotal)
                }
            else:
                taxes = []
                aline_ice = 0.0
                include_tax = False
                for tax_line in line.invoice_line_tax_ids:
                    if tax_line.tax_group_id.type == 'ice':
                        aline_ice += float('{:.2f}'.format((line.price_subtotal * tax_line.amount) / 100))
                    if tax_line.tax_group_id.type == 'iva' and tax_line.price_include:
                        include_tax = True
                codePrincipal = line._get_name_line_product()
                price = line.price_unit * (1 - (line.discount or 0.00) / 100.0)
                discount = line.discount if line.type_discount == 'fixed' else (line.price_unit - price) * line.quantity
                price_unit = line.price_unit if not include_tax else abs((line.price_subtotal + discount) / line.quantity)
                description = utils.fix_chars(line.name.strip())
                detail = {
                    'codigoPrincipal': codePrincipal,
                    'descripcion': description[0: 300],
                    'cantidad': '%.6f' % (line.quantity),
                    'precioUnitario': '%.6f' % (price_unit),
                    'descuento': '%.2f' % discount,
                    'precioTotalSinImpuesto': '%.2f' % (line.price_subtotal)
                } 
                for tax_line in line.invoice_line_tax_ids:
                    if tax_line.tax_group_id.type in ['iva', 'iva0', 'ice', 'exiva', 'nobiva']:
                        price_unit = line.price_subtotal
                        if tax_line.tax_group_id.type == 'iva':
                            codePor = utils.codeTax[str(int(tax_line.amount))]
                            price_unit += aline_ice
                        else:
                            codePor = tax_line.form_code_ats
                        tax = {
                            'codigo': tax_line.tax_group_id.code,
                            'codigoPorcentaje': codePor,
                            'tarifa': int(tax_line.amount),
                            'baseImponible': '{:.2f}'.format(price_unit),
                            'valor': '{:.2f}'.format((price_unit * tax_line.amount) / 100) 
                        }
                        taxes.append(tax)
                detail.update({'impuestos': taxes})
            details.append(detail)
        return {'detalles': details}
    
    def _destinations(self):
        destinations = dict()
        for line in self.transport_permit_ids:
            destinations.update({
                'dirPartida': utils.fix_chars(line.address_starting),
                'dirDestinatario': utils.fix_chars(self.partner_invoice_id._display_address1()),
                'fechaIniTransporte': utils.fix_date(line.date_transport),
                'fechaFinTransporte': utils.fix_date(line.date_due),
                'razonSocialTransportista': utils.fix_chars(line.partner_id.name),
                'tipoIdentificacionTransportista': line.partner_id.l10n_latam_identification_type_id.code,
                'rucTransportista': line.partner_id.vat,
                'placa': line.license_plate,
            })
            destination = list()
            for xline in line.transport_permit_line_ids:
                vals = {
                    'motivoTraslado': utils.fix_chars(xline.reason),
                    'docAduaneroUnico': xline.customs_document,
                    'codEstabDestino': xline.code_destination_business,
                    'ruta': utils.fix_chars(xline.route),
                }
                destination.append(vals)
            destinations.update({'destinos': destination})
        return destinations   

    @api.multi
    def _refunds(self):
        refunds = []
        val_refunds = {
            'codDocReembolso': 41,
            'totalComprobantesReembolso': 0.0,
            'totalBaseImponibleReembolso': 0.0,
            'totalImpuestoReembolso': 0.0,
            'reembolsos': [],
        }
        for line in self.refund_ids:
            partner = line.partner_id
            auth_ref = line.authorization_id
            if not partner.country_id:
                partner.country_id = self.env.ref('base.ec')
            vals = {
                'tipoIdentificacionProveedorReembolso': partner.l10n_latam_identification_type_id.code,
                'identificacionProveedorReembolso': partner.vat,
                'codPaisPagoProveedorReembolso': partner.country_id.phone_code,
                'tipoProveedorReembolso': partner.type_supplier,
                'codDocReembolso': line.type_document_id.code,
                'estabDocReembolso': auth_ref.entity,
                'ptoEmiDocReembolso': auth_ref.issue,
                'secuencialDocReembolso': line.number,
                'fechaEmisionDocReembolso': utils.fix_date(line.date_invoice),
                'numeroautorizacionDocReemb': line.authorization_number if line.is_electronic else line.authorization_id.name,
            }
            totalConImpuestos = self._taxes(line.tax_line_ids)
            for line_tax in totalConImpuestos:
                line_tax['baseImponibleReembolso'] = line_tax['baseImponible']
                line_tax['impuestoReembolso'] = line_tax['valor']
                del line_tax['baseImponible']
                del line_tax['valor']
                val_refunds['totalBaseImponibleReembolso'] += float(line_tax['baseImponibleReembolso'])
                val_refunds['totalImpuestoReembolso'] += float(line_tax['impuestoReembolso'])
            vals['detalleImpuestos'] = totalConImpuestos
            refunds.append(vals)
        val_refunds['totalComprobantesReembolso'] = val_refunds['totalBaseImponibleReembolso'] + val_refunds['totalImpuestoReembolso']
        val_refunds['reembolsos'] = refunds
        return val_refunds

    def _infoAdicional(self):
        lines = []
        for line in self.line_info_ids:
            lines.append("""<campoAdicional nombre="%s">%s</campoAdicional>""" % (line.name, line.value_tag))
        infoAdicional = {'infoAdicional': lines}
        return infoAdicional

    @api.multi
    def invoice_print(self):
        self.ensure_one()
        self.sent = True
        if self.user_has_groups('account.group_account_invoice', 'oe_edocs.group_account_invoice_electronic'):
            return self.env.ref('account.account_invoices').report_action(self)
    
    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        if self.authorization:
            name_report = self.authorization_number
        else:
            name_report = '%s %s' % (self.type_document_id.short_name, self.name or self.number)
        return name_report

    def _compute_discount(self, details):
        total = sum(float(det['descuento']) for det in details['detalles'])
        return {'totalDescuento': '{:.4f}'.format(total)}

    @api.multi
    def _get_barcode(self):
        self.ensure_one()
        fp = io.BytesIO()
        generate('code128', self.access_key, output=fp, writer_options={'font_size': 0})
        return base64.b64encode(fp.getvalue())

    @api.multi
    def action_views_transport_permit(self):
        transport_line_ids = self.env['transport.permit.line'].search([('invoice_id', '=', self.id)])
        transport_ids = transport_line_ids.mapped('transport_permit_id')
        action_name = 'oe_edocs.action_transport_permit_out_form'
        xml_name = 'oe_edocs.view_transport_permit_out_form'
        action = self.env.ref(action_name).read()[0]
        if len(transport_ids) > 1:
            action['domain'] = [('id', 'in', transport_ids.ids)]
        elif len(transport_ids) == 1:
            action['views'] = [(self.env.ref(xml_name).id, 'form')]
            action['res_id'] = transport_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def _get_details(self):
        result = []
        for line in self.invoice_line_ids:
            values = {
                'product_id': line.product_id.id,
                'code_main': line.product_id.default_code or line.product_id.barcode,
                'name': line.name,
                'quantity': line.quantity,
            }
            result.append((0, 0, values))
        return result

    def _get_line_details(self):
        result = []
        line_details = self._get_details()
        vals = {
            'invoice_id': self.id,
            'tmpl_invoice_number': self.name,
            'tmpl_invoice_date': self.date_invoice,
            'route': '%s %s' % (self.company_id.partner_id.city or '', self.partner_id.city or ''),
            'reason': _('Sale'),
            'addressee_id': self.company_id.partner_id.id,
            'destination_id': self.partner_id.id,
            'transport_permit_line_details_ids': line_details,
        }
        result.append((0, 0, vals))
        return result

    @api.multi
    def action_transport_permit(self):
        self.ensure_one()
        if self.type == 'out_invoice':
            action = self.env.ref('oe_edocs.action_transport_permit_out_form').read()[0]
        type_document = self.env['account.type.document'].search([('code', '=', '06')], limit=1).id
        line_details = self._get_line_details()
        action.update({
            'views': [tuple(action['views'][1])],
            'res_id': False,
            'context': self.with_context(default_type_document_id=type_document,
                                         default_type='out_transport',
                                         default_tmpl_entity=self.authorization_id.entity,
                                         default_tmpl_emission=self.authorization_id.issue,
                                         default_tmpl_invoice_number=self.name,
                                         default_tmpl_invoice_date=self.date_invoice,
                                         default_origin=self.name,
                                         #default_invoice_id=self.id,
                                         default_addressee_id=self.partner_id.id,
                                         default_address_starting=self.company_id.city or '',
                                         default_transport_permit_line_ids=line_details)._context,
        })
        return action

    @api.multi
    def render_qweb_xml(self, invoice_id):
        domain = [('res_model', '=', self._name), ('res_id', '=', invoice_id.id), ('datas_fname', '=', '%s.xml' % invoice_id.access_key)]
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


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    def _get_view_product(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        result = ir_config.get_param('view.code.product').lower() == 'true'
        return result
    
    def _get_name_line_product(self):
        codePrincipal = ''
        if self.product_id:
            codePrincipal = self.product_id.default_code or self.name[:25]
        else:
            codePrincipal = self.name[:25]
        if len(codePrincipal) > 25: codePrincipal = codePrincipal[0: 25]
        codePrincipal = utils.fix_chars(codePrincipal)
        return codePrincipal
