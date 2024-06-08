# -*- coding: utf-8 -*-

import base64
import calendar
from datetime import datetime
import logging
import os

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import NameOID

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

_logger = logging.getLogger(__name__)

class Company(models.Model):
    _inherit = 'res.company'

    def _compute_web_url(self):
        param_id = self.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1)
        return '%s/downloads_documents' % param_id.value

    environment = fields.Selection([
        ('test', 'Test'),
        ('prod', 'Production')], string='Environment',
        default='test', required=True, help='Enabling the testing environment, otherwise it will be in production.')
    password_signed = fields.Char(string='Password', size=50, store=True, copy=False, help='Password used to open the electronic signature.')
    signed_digital = fields.Binary(string='File Content')
    filename = fields.Char('File Name')
    password_crypt = fields.Char(string='Encrypted Password', invisible=True, copy=False)
    sender_name = fields.Char(string='Sender Name', size=150, copy=False, help='Sender name of the person sending the email')
    enable_signer = fields.Datetime(string='Date of Issue', readonly=True, copy=False, help='Date of issue of the electronic signature')
    due_signer = fields.Datetime(string='Date of Expiry', readonly=True, copy=False, help='Expiration date of the electronic signature')
    name_issuer = fields.Char(string='Certificate issued by', readonly=True, copy=False)
    name_subject = fields.Char(string='Issued to', readonly=True, copy=False)
    state_signer = fields.Selection(selection=[('unverified', 'Unverified'), ('valid', 'Valid'), ('expired', 'Expired')],
        string='State Signer', default='unverified')
    url_web = fields.Char(compute='_compute_web_url', string='Url Download')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'history_documents')
        self.env.cr.execute("""CREATE VIEW history_documents AS 
            (SELECT i.id AS id, i.date_invoice AS date, i.type AS "type", i.name AS "name", i.environment AS env, i.company_id
            FROM account_invoice i
            WHERE i.is_electronic=True AND i.authorization=True AND i.type IN ('out_invoice', 'out_refund')
            UNION
            SELECT w.id AS id, w.date_withholding AS date, w.type AS "type", w.name AS "name", w.environment AS env, w.company_id
            FROM account_withholding w
            WHERE w.is_electronic=True and w.authorization=True AND w.type = 'out_withholding')""")

    def load_cert_pk12(self, filecontent):
        try:
            _logger.info(_('Pass: %s') % self.password_signed)
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(filecontent, self.password_signed.encode('utf8'), backend=None)
            attr_subject = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
            attr_date_after = certificate.not_valid_after
            for cert in additional_certificates:
                subject = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
                date_after = cert.not_valid_after
                if attr_subject.value == subject.value and attr_date_after <= date_after:
                    certificate = cert
            enable_signer = certificate.not_valid_before.strftime('%Y-%m-%d %H:%M:%S')
            due_signer = certificate.not_valid_after.strftime('%Y-%m-%d %H:%M:%S')
            attr_issuer = certificate.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0]
            has_expired = False if datetime.now() <= certificate.not_valid_after else True
            vals = {
                'enable_signer': enable_signer,
                'due_signer': due_signer,
                'state_signer': 'expired' if has_expired else 'valid',
                'name_issuer': attr_issuer.value,
                'name_subject': attr_subject.value,
            }
            self.write(vals)
        except Exception as e:
            _logger.error('Error: %s' % e)
            raise UserError(_('You can not validate the electronic signature entered, verify the password or re-enter the signature again %s') % e)

    @api.multi
    def action_check_signature(self):
        self.ensure_one()
        filecontent = base64.b64decode(self.signed_digital)
        self.load_cert_pk12(filecontent)

    @api.multi
    def toggle_environment_value(self):
        prod = self.filtered(lambda process: process.environment == 'prod')
        prod.write({'environment': 'test'})
        (self - prod).write({'environment': 'prod'})
    
    def _generation_signed(self):
        path = '/tmp/%s/' % self._cr.dbname
        if not os.path.isdir(path):
            os.makedirs(path, mode=0o777)
        path_pk12 = '%s%s' % (path, self.filename)
        if self.signed_digital and (not os.path.exists(path_pk12) or len(self.signed_digital) == 0 or os.path.getsize(path_pk12) == 0):
            if os.path.exists(path_pk12) and os.path.getsize(path_pk12) == 0: os.remove(path_pk12)
            if len(self.signed_digital) == 0: raise UserError(_('The electronic signature is damaged'))
            file_signed = open(path_pk12, 'wb')
            file_signed.write(base64.b64decode(self.signed_digital))
            file_signed.close()
            logging.info('Archivo creado .P12')
        if os.path.exists(path_pk12):
            return self.password_signed, self.filename
        else:
            return False, False

# UNION
# SELECT t.id AS id, t.date_transport AS date, t.type AS "type", t.name AS "name", t.environment AS env, t.company_id
# FROM transport_permit t
# WHERE t.is_electronic=True and t.authorization=True AND t.type = 'out_transport'

    def _get_number_docs(self):
        num = self._get_count_document()
        if num >= self.number_limit:
            raise UserError(_('Exceeded the limit of sending electronic documents'))

    def _get_review_message(self):
        num = self._get_count_document()
        xpercentage = (num * 100) / self.number_limit
        if xpercentage >= 90.0:
            self.env.user.notify_info(_('A consumed more than 90% of your package.'))
        if self.environment == 'test':
            self.env.user.notify_info(_('You are in a TEST environment when sending to the SRI.'))

    def _get_count_document(self):
        date = datetime.strptime(fields.Date.context_today(self), DF)
        day_from, day_to = calendar.monthrange(date.year, date.month)
        date_from = date.replace(day=1)
        date_to = date.replace(day=day_to)
        sql = """SELECT COUNT(id) AS number FROM history_documents WHERE company_id = '%s' AND date >= '%s' AND date <= '%s'""" % (self.id, date_from, date_to)
        self.env.cr.execute(sql)
        num = self.env.cr.fetchone()
        return num[0]

    @api.model
    def review_document_xml(self):
        list_model = ['account.invoice', 'account.withholding', 'transport.permit']
        domain = [('state', 'in', ['approved', 'open', 'paid']), ('received', '=', True), ('authorization', '=', False)]
        for model in list_model:
            doc_ids = self.env[model].search(domain, limit=50, order='id asc')
            i = 0
            max_docs = len(doc_ids)
            for doc in doc_ids:
                i += 1
                doc.with_context(cron=True).action_validate_to_sri()
                _logger.info('Number documents %s of %s' % (i, max_docs))
        company_ids = self.search([('environment', '=', 'prod')])
        for company in company_ids:
            company.action_check_signature()
        _logger.info('Finish process authorization')
