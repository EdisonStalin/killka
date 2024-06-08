# -*- coding: utf-8 -*-

import base64
import io
import logging
import time
import uuid

from barcode import generate

from odoo import models, api, fields, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

from . import utils


_logger = logging.getLogger(__name__)


class TransportPermit(models.Model):
    _name = 'transport.permit'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "transport permit"
    _order = "date_transport desc, number desc, id desc"

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    number = fields.Char(string='Number', readonly=False, size=9, copy=False, default='000000000')
    internal_number = fields.Integer('Internal Number', default=0, copy=False)
    name = fields.Char(string='Reference/Description', index=True, default='Nuevo',
        readonly=True, states={'draft': [('readonly', False)]}, copy=False, help='The name that will be used on transport permit')
    type_document_id = fields.Many2one('account.type.document', string='Voucher type', change_default=True, copy=True,
                                       readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    access_token = fields.Char('Security Token', copy=False, default=_get_default_access_token)
    comment = fields.Text('Additional Information', copy=True, readonly=True, states={'draft': [('readonly', False)]})
    sent = fields.Boolean(readonly=True, default=False, copy=False, help="It indicates that the transport has been sent.")
    date_emission = fields.Date(string='Emission Date', copy=True, readonly=True, states={'draft': [('readonly', False)]}, index=True,
        default=fields.Date.context_today, help="Keep empty to use the current date")
    rise = fields.Char(string='Rise', size=40, copy=True, readonly=True, states={'draft': [('readonly', False)]}, help='Message of relationship with the document')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft', track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed transport permit.\n"
             " * The 'Approved' status is used when user creates transport permit, an transport permit number is generated.\n"
             " * The 'Cancelled' status is used when user cancel transport permit.")
    sequence_number_next = fields.Char(string='Next Number', compute="_get_sequence_number_next", inverse="_set_sequence_next")
    sequence_number_next_prefix = fields.Char(string='Next Number', compute="_get_sequence_prefix")
    line_info_ids = fields.One2many('additional.info', 'transport_id', string='Information Additional Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    invoice_id = fields.Many2one('account.invoice', 'Origin invoice', readonly=True)
    transport_permit_line_details_ids = fields.One2many('transport.line.details', 'transport_permit_id', string='Transport Permit Line Detalle')
    transport_permit_line_ids = fields.One2many('transport.permit.line', 'transport_permit_id', string='Transport Permit Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('transport.permit'))
    user_id = fields.Many2one('res.users', string='Responsible', track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user, copy=False)
    origin = fields.Char(string='Source Document', copy=True, help="Reference of the document that produced this transport.",
        readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([
            ('out_transport', 'Transport Outbound'),
            ('in_transport', 'Transport Inbound')], copy=True, readonly=True, index=True, change_default=True,
        default='out_transport', track_visibility='always')
    
    address_starting = fields.Char('Address Starting', size=200, required=True, copy=True, default='Quito',
        readonly=True, states={'draft': [('readonly', False)]}, help='Starting address where the vehicle leaves')
    date_transport = fields.Date(string='Transport start', readonly=True, required=True, states={'draft': [('readonly', False)]}, index=True,
        default=fields.Date.context_today, help="Keep empty to use the current date", copy=False)
    date_due = fields.Date(string='Transport finish', readonly=True, required=True, states={'draft': [('readonly', False)]}, index=True,
        default=fields.Date.context_today, help="Keep empty to use the current date", copy=False)
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True, copy=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    license_plate = fields.Char('License plate', size=10, copy=True, required=True,
        readonly=True, states={'draft': [('readonly', False)]},)
    
    authorization_id = fields.Many2one('account.authorization', string='Authorization', change_default=True,
        readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    manual_sequence = fields.Boolean(related='authorization_id.manual_sequence')
    is_electronic = fields.Boolean(string='Is electronic', copy=True, default=True, help='Select you have the possibility of sending the electronic document to the SRI')
    authorization = fields.Boolean('Authorized by SRI', copy=False, help='Selected indicates that the invoice is authorized by the SRI')
    received = fields.Boolean('Received by SRI', copy=False, help='Selected indicates that the invoice is received by the SRI')
    access_key = fields.Char('Access key', size=49, copy=False, help='Access code generated by the company to be validated')
    authorization_date = fields.Char('Authorization date', size=100, copy=False, readonly=True, help='Authorization date validated by SRI')
    authorization_number = fields.Char('N° authorization', size=49, copy=False, readonly=True, help='Authorization number validated by SRI')
    environment = fields.Char('Environment', size=50, copy=False, readonly=True)
    emission_code = fields.Char('Type the emssion', size=1, default='2', copy=False, readonly=True)
    message_state = fields.Char('Message Authorization', size=25, copy=False, readonly=True)
    edi_document_ids = fields.One2many('account.edi.document', 'transport_id', 'History')
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

    def _get_line_specific_history(self, action):
        line = self.env['account.edi.document']
        if len(self.edi_document_ids) > 0:
            domain = [('id', 'in', self.edi_document_ids.ids), ('type', '=', action)]
            line = line.search(domain, limit=1, order='id desc')
        return line

    @api.depends('state', 'authorization_id', 'edi_document_ids', 'is_electronic', 'authorization')
    def _get_sequence_prefix(self):
        for transport in self:
            if transport.authorization_id:
                transport.sequence_number_next_prefix = '%s-%s-' % (transport.authorization_id.entity, transport.authorization_id.issue)
            else:
                transport.sequence_number_next_prefix = '000-000-'

    @api.depends('state', 'authorization_id')
    def _get_sequence_number_next(self):
        for transport in self:
            if transport.state not in ['draft']:
                if transport.number: transport.sequence_number_next = '%s' % transport.number
            else:
                if not transport.number:
                    transport.sequence_number_next = '000000000'
                    transport.number = transport.sequence_number_next
                else:
                    if len(transport.number) < 9:
                        transport.number = '%%0%sd' % '9' % int(transport.internal_number)
                    transport.sequence_number_next = transport.number

    @api.model
    def create(self, vals):
        details = []
        if 'transport_permit_line_details_ids' in vals:
            details = vals['transport_permit_line_details_ids']
        if 'invoice_id' in vals:
            invoice_id = self.env['account.invoice'].browse(vals['invoice_id'])
            if invoice_id.substitute_permit:
                vals.update({
                    'date_emission': invoice_id.date_invoice,
                    'number': invoice_id.number,
                    'internal_number': invoice_id.internal_number,
                })
                for x, y, z in vals['transport_permit_line_ids']:
                    if not z.get('invoice_id', False) or z.get('invoice_id', False) != invoice_id.id:
                        z['invoice_id'] = invoice_id.id
                    if 'transport_permit_line_details_ids' not in z:
                        z['transport_permit_line_details_ids'] = details
                if 'transport_permit_line_details_ids' in vals:
                    vals.pop('transport_permit_line_details_ids')
        return super(TransportPermit, self).create(vals)

    @api.multi
    def _set_sequence_next(self):
        if self.manual_sequence or not self.sequence_number_next:
            return False
        self.authorization_id._set_sequence_next("transport_permit", "('approved', 'cancel')")

    @api.model
    def default_get(self, default_fields):
        res = super(TransportPermit, self).default_get(default_fields)
        if not res.get('type_document_id', False):
            res['type_document_id'] = self.env['account.type.document'].search([('code', '=', '06')], limit=1).id
        if not res.get('authorization_id', False):
            domain = [('company_id', '=', self.env.user.company_id.id), ('is_electronic', '=', True), ('type_document_id', '=', res.get('type_document_id', False))]
            auth = self.env['account.authorization'].search(domain, limit=1, order="id asc")
            res['authorization_id'] = auth.id
        return res

    def get_mail_url(self):
        return self.get_share_url()

    def _get_details(self, lines):
        result = []
        for line in lines:
            values = {
                'product_id': line.product_id.id,
                'code_main': line.product_id.default_code or line.product_id.barcode,
                'name': line.name,
                'quantity': line.quantity,
            }
            result.append((0, 0, values))
        return result

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = {'value': {}}
        if self.partner_id and self.invoice_id:
            lines = self.invoice_id.invoice_line_ids
            res['value']['date_emission'] = self.invoice_id.date_invoice
            res['value']['transport_permit_line_details_ids'] = self._get_details(lines)
        return res

    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        return  self.type == 'out_transport' and self.state == 'draft' and _('Draft Transport Permit') or \
                self.type == 'out_transport' and self.state == 'approved' and not self.authorization and _('Transport Permit - %s') % (self.name) or \
                self.type == 'out_transport' and self.state == 'approved' and self.authorization and '%s' % (self.authorization_number) or \
                self.type == 'in_transport' and self.state == 'draft' and _('Vendor Transport Permit') or \
                self.type == 'in_transport' and self.state == 'approved' and not self.authorization and _('Transport Permit - %s') % (self.name) or \
                self.type == 'in_transport' and self.state == 'approved' and self.authorization and '%s' % (self.authorization_number)

    @api.multi
    def action_transport_sent(self):
        """ Open a window to compose an email, with the edi transport permit template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('oe_edocs.mail_template_data_notification_email_transport_permit', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='transport.permit',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="account.mail_template_data_notification_email_account_invoice",
            force_email=True
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _create_fist_history(self):
        if not len(self.edi_document_ids):
            vals = {
                'sequence': 10,
                'code': 0,
                'transport_id': self.id,
                'type': 'ENVIAR',
                'add_information': self.access_key,
            }
            self.env['account.edi.document'].create(vals)

    @api.multi
    def action_restore_doc(self):
        self.ensure_one()
        self._validate_transport()

    @api.multi
    def action_send_to_sri(self):
        self.ensure_one()
        cron = self._context.get('cron', False)
        if self.state in ['draft', 'cancel']: return False
        if self.invoice_id.substitute_permit and self.invoice_id.authorization:
            self.write({
                'access_key': self.invoice_id.access_key,
                'authorization_number': self.invoice_id.authorization_number,
                'environment': self.invoice_id.environment,
                'authorization_date': self.invoice_id.authorization_date,
                'message_state': self.invoice_id.message_state,
                'received': self.invoice_id.received,
                'authorization': self.invoice_id.authorization,
            })
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
        vals.update(self._info_transport())
        vals.update({'claveAcceso': self.access_key})
        vals.update(self._destinations())
        doc_tmpl = utils._get_type_document(self.type_document_id.code)
        return doc_tmpl.render(vals)

    def _info_transport(self):
        company = self.company_id
        driver = self.partner_id
        if not driver.l10n_latam_identification_type_id:
            raise UserError(_('The driver is not validated correctly'))
        establ = self.authorization_id.establishment_id
        if establ:
            dirEstablecimiento = utils.fix_chars(establ._display_address())
        else:
            dirEstablecimiento = utils.fix_chars(company.partner_id._display_address())
        infoGuiaRemision = {
            'dirEstablecimiento': dirEstablecimiento,
            'dirPartida': utils.fix_chars(self.address_starting),
            'razonSocialTransportista': driver.name,
            'tipoIdentificacionTransportista': driver.l10n_latam_identification_type_id.code,
            'rucTransportista': driver.vat,
            'obligadoContabilidad': 'SI' if company.partner_id.check_accounting else 'NO',
            'fechaIniTransporte': utils.fix_date(self.date_transport),
            'fechaFinTransporte': utils.fix_date(self.date_due),
            'placa': self.license_plate,
        }
        if self.rise:
            infoGuiaRemision.update({'rise': self.rise})
        if company.company_registry:
            infoGuiaRemision.update({'contribuyenteEspecial': company.company_registry[:13]})
        return infoGuiaRemision

    def _destinations(self):
        destinatarios = []
        for line in self.transport_permit_line_ids:
            invoice = line.invoice_id or False
            invoice_number = line.tmpl_invoice_number or invoice.name
            invoice_code = invoice.type_document_id.code if invoice else '18'
            authorization_number = invoice.access_key if invoice else ''
            date_invoice = invoice and invoice.date_invoice or line.tmpl_invoice_date
            destinatario = {
                'identificacionDestinatario': line.destination_id.vat,
                'razonSocialDestinatario': line.destination_id.name,
                'dirDestinatario': '%s %s' % (line.destination_id.street, line.destination_id.street2 or ''),
                'motivoTraslado': line.reason,
                'docAduaneroUnico': line.customs_document,
                'codEstabDestino': line.code_destination_business,
                'ruta': line.route,
                'codDocSustento': invoice_code,
                'numDocSustento': invoice_number,
                'numAutDocSustento': authorization_number,
                'fechaEmisionDocSustento': self.fix_date(date_invoice),
                'detalles': self._details(),
            }
            destinatarios.append(destinatario)
        return {'destinatarios': destinatarios}

    def _details(self):
        details = []
        for line in self.transport_permit_line_details_ids:
            if line.product_id:
                codePrincipal = utils.fix_chars(line.product_id.default_code or line.product_id.name[:25]) or '000'
            else:
                codePrincipal = utils.fix_chars(line.name[:25] or '000')
            detail = {
                'codigoInterno': codePrincipal,
                'codigoAdicional': codePrincipal,
                'descripcion': utils.fix_chars(line.name.strip()[:300]),
                'cantidad': '%.2f' % (line.quantity),
            }
            details.append(detail)
        return details

    @api.multi
    def action_transport_approved(self):
        to_open_transport = self.filtered(lambda transport: transport.state != 'open')
        if to_open_transport.filtered(lambda transport: transport.state != 'draft'):
            raise UserError(_('Transport must be in draft state in order to validate it.'))
        if not self.date_transport: self.date_transport = fields.Date.context_today(self)
        self._validate_transport()
        self._create_fist_history()
        for transport in self:
            inv = transport.invoice_id
            if inv.substitute_permit:
                transport.write({
                    'date_emission': inv.date_invoice,
                    'number': inv.number,
                    'internal_number': inv.internal_number,
                    'name': inv.name,
                    'access_key': inv.access_key,
                })
        return True

    def _generate_key_access(self):
        if self.is_electronic and self.type_document_id.is_electronic and (not\
            self.access_key or not self.received or not self.authorization):
            access_key = self.authorization_id.generation_access_key(self.name, self.type_document_id, self.date_emission)
        else:
            access_key = self.access_key
        return access_key

    def _get_sequence(self):
        padding = 9
        if not self.authorization_id.manual_sequence:
            if not self.authorization_id.sequence_id and self.authorization_id.is_electronic and self.authorization_id.type == 'internal':
                raise UserError(_('The authorizations do not have a sequence!'))
            sequence_id = self.authorization_id.sequence_id._get_current_sequence()
            padding = sequence_id and sequence_id.padding
            if self.number == '000000000' or not self.number:
                name_old = self.sequence_number_next_prefix + self.sequence_number_next
                if name_old != self.name or self.number == '000000000':
                    self.internal_number = sequence_id.number_next_actual
            else:
                self.internal_number = int(self.number)
        else:
            if self.number == '000000000': raise UserError(_('Enter the document number!'))
            self.internal_number = int(self.number)
        self.sequence_number_next = '%%0%sd' % padding % self.internal_number
        self.number = self.sequence_number_next
        name = '%s%s' % (self.sequence_number_next_prefix, self.number)
        self.name = name

    def _validate_transport(self):
        self._get_sequence()
        return self.write({'state': 'approved', 'access_key': self._generate_key_access()})

    @api.onchange('type_document_id', 'is_electronic', 'partner_id')
    def _onchange_is_electronic(self):
        res = {'domain': {}}
        domain = [('type_document_id', '=', self.type_document_id.id), ('is_electronic', '=', self.is_electronic)]
        if self.type == 'in_transport': 
            domain = [('partner_id', '=', self.partner_id.id)]
            self.authorization = True if self.is_electronic else False
        user = self.env.user
        if self.type == 'out_transport':
            domain += [('type', '=', 'internal')]
            if len(user.authorization_ids) > 1:
                ids = user.authorization_ids.ids
                domain += [('id', 'in', ids)]
        res['domain'] = {'authorization_id': domain}
        comment = ""
        if not self.authorization_id:
            auth = self._get_authorization(domain)
            if auth: self.authorization_id = auth.id
        else:
            comment = self.authorization_id.comment
        self.comment = comment
        return res

    def _get_authorization(self, domain):
        domain += [('company_id', '=', self.env.user.company_id.id)]
        auth = self.env['account.authorization'].search(domain, limit=1, order="id asc")
        # if not auth: raise UserError(_('Does not have physical or electronic authorizations, create a new physical or electronic authorization'))
        return auth

    @api.multi
    def action_transport_cancel(self):
        if self.filtered(lambda tra: tra.state not in ['draft', 'approved']):
            raise UserError(_("Transport Permit must be in draft or open state in order to be cancelled."))
        return self.action_cancel()

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def action_transport_draft(self):
        vals = {'state': 'draft'}
        if self.filtered(lambda tra: tra.state != 'cancel'):
            raise UserError(_("Transport Permit must be cancelled in order to reset it to draft."))
        # go from canceled state to draft state
        if not self.authorization: vals.update({'number': '000000000', 'internal_number': 0})
        self.write(vals)
        if not self.authorization:
            sequence_id = self.authorization_id.sequence_id._get_current_sequence()
            self.sequence_number_next = '%%0%sd' % sequence_id.padding % sequence_id.number_next_actual
        return True

    @api.multi
    def unlink(self):
        for transport in self:
            if transport.state in ('approved', 'cancel'):
                raise UserError(_('You cannot delete an transport permit which is not draft.'))
            elif transport.type == 'out_transport' and transport.authorization:
                raise UserError(_('You cannot delete an transport permit after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(TransportPermit, self).unlink()

    def fix_date(self, date):
        d = time.strftime('%d/%m/%Y', time.strptime(date, '%Y-%m-%d'))
        return d

    @api.multi
    def _get_barcode(self):
        self.ensure_one()
        fp = io.BytesIO()
        generate('code128', self.access_key, output=fp, writer_options={'font_size': 0})
        return base64.b64encode(fp.getvalue())

    @api.multi
    def render_qweb_xml(self, transport_id):
        domain = [('res_model', '=', self._name), ('res_id', '=', transport_id.id), ('datas_fname', '=', '%s.xml' % transport_id.access_key)]
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


class TransportPermitLine(models.Model):
    _name = 'transport.permit.line'
    _description = "transport permit line"
    _order = "sequence,id"

    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying the transport permit.")
    transport_permit_id = fields.Many2one('transport.permit', string='Transport Permit Reference', ondelete='cascade', index=True)        
    invoice_id = fields.Many2one('account.invoice', string='Document')
    reason = fields.Char('Other Reason', size=250, default='Venta', help='Enter a reason why you are generating the transport permit')
    customs_document = fields.Char('Customs Document', size=200, help='Description customs document')
    code_destination_business = fields.Char('Business Destination Code', size=3, help='Business destination code')
    route = fields.Char('Route', size=250, required=True, default='Quito-Guayaquil', help='Sending Route')
    company_id = fields.Many2one('res.company', string='Company',
        related='transport_permit_id.company_id', store=True, readonly=True, related_sudo=False)
    
    tmpl_invoice_number = fields.Char('Temporary Entity', size=17, default='000-000-000000000', help='Number of document')
    tmpl_invoice_date = fields.Date('Temporary Date invoice', default=fields.Date.context_today, help='Date invoice emission')
    authorization_number = fields.Char('N° authorization', size=49, copy=False, readonly=True, help='Authorization number validated by SRI')
    addressee_id = fields.Many2one('res.partner', string='Addressee', change_default=True)
    destination_id = fields.Many2one('res.partner', string='Destination', change_default=True)
    transport_permit_line_details_ids = fields.One2many('transport.line.details', 'transport_line_detail_id', string='Transport Permit Line Detalle', copy=True)

    @api.model
    def create(self, vals):
        res = super(TransportPermitLine, self).create(vals)
        for line in res.transport_permit_line_details_ids:
            if not line.transport_permit_id:
                line.transport_permit_id = res.transport_permit_id
        return res

    @api.model
    def default_get(self, default_fields):
        res = super(TransportPermitLine, self).default_get(default_fields)
        if 'addressee_id' not in res:
            res['addressee_id'] = self.env.user.company_id.partner_id.id
        return res

    @api.onchange('invoice_id')
    def onchage_invoice_id(self):
        lines = []
        if self.invoice_id:
            lines = self._get_details(self.invoice_id.invoice_line_ids)
            self.tmpl_invoice_number = self.invoice_id.name
            self.tmpl_invoice_date = self.invoice_id.date_invoice
            self.authorization_number = self.invoice_id.is_electronic and self.invoice_id.authorization_number or False
            self.addressee_id = self.env.user.company_id.partner_id
            self.destination_id = self.invoice_id.partner_id
        self.transport_permit_line_details_ids = lines

    def _get_details(self, lines):
        result = []
        for line in lines:
            values = {
                'product_id': line.product_id.id,
                'code_main': line.product_id.default_code or line.product_id.barcode,
                'name': line.name,
                'quantity': line.quantity,
            }
            result.append((0, 0, values))
        return result

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, '%s - %s' % (record.route, record.reason)))
        return res

    @api.multi
    def unlink(self):
        if self.filtered(lambda r: r.transport_permit_id and r.transport_permit_id.state != 'draft'):
            raise UserError(_('You can only delete an transport permit line if the transport permit is in draft state.'))
        return super(TransportPermitLine, self).unlink()


class TransportLineDetails(models.Model):
    _name = 'transport.line.details'
    _description = "transport line details"
    _order = "sequence,id"
    
    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying the transport permit.")
    name = fields.Text(string='Description', required=True, copy=True)
    transport_permit_id = fields.Many2one('transport.permit', string='Transport Permit Reference', ondelete='cascade', index=True) 
    transport_line_detail_id = fields.Many2one('transport.permit.line', string='Transport Permit Reference Line', ondelete='cascade', index=True, copy=True)        
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', index=True, copy=True)
    code_main = fields.Char(string='Code Main', size=25, copy=True)
    code_assistant = fields.Char(string='Code Assistant', size=25, copy=True)
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1, copy=True)
    company_id = fields.Many2one('res.company', string='Company',
        related='transport_line_detail_id.company_id', store=True, readonly=True, related_sudo=False)

    #@api.onchange('transport_line_detail_id', 'apply_apu', 'purchase_type')
    #def _onchange_apu_id(self):
    #    res = {'domain': {}}
    #    if self.transport_line_detail_id:
    #        transport_line_detail_id = self.env['transport.permit.line']
    #        res['domain']['transport_line_detail_id'] = [('id', 'in', transport_line_detail_id.ids)]
    #    return res

    def _get_details(self, lines):
        result = []
        for line in lines:
            values = {
                'product_id': line.product_id.id,
                'code_main': line.product_id.default_code or line.product_id.barcode,
                'name': line.name,
                'quantity': line.quantity,
            }
            result.append((0, 0, values))
        return result

    def _get_name_line_product(self):
        codePrincipal = '/'
        if self.product_id:
            if self.product_id.default_code:
                codePrincipal = self.product_id.default_code
            else:
                codePrincipal = self.product_id.name or '000'
        else:
            codePrincipal = self.name[:25]
        if len(codePrincipal) > 25: codePrincipal = codePrincipal[0: 25]
        codePrincipal = utils.fix_chars(codePrincipal)
        return codePrincipal

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.name = self.product_id.name
            self.code_main = self.product_id.default_code or self.product_id.barcode

