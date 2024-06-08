#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, fields


class CodeValidationDocument(models.Model):
    _name = "code.validation.document"
    _description = "Error and Alert of Validation Code"
    _order = 'code asc'
    
    code = fields.Integer(string='Code', requerid=True, help='Result code of the SRI')
    name = fields.Char(string='Description', size=250, required=True, help='Error and Alert of result')
    message_solution = fields.Text(string='Solution message', required=True)
    type_action = fields.Selection(selection=[('send', 'Send'),
                                              ('resend', 'Resend'),
                                              ('none', 'None'), ])
    type_validation = fields.Selection(selection=[('AUT', 'Authorization'),
                                                  ('REC', 'Reception'),
                                                  ('EMI', 'Emission'),
                                                  ('none', 'None')], string='Validation Type', help='Validation type information SRI')
    active = fields.Boolean(string='Active', default=True)
    
