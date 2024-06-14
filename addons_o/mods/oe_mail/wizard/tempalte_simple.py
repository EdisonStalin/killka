#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, fields

class TemplateSimple(models.Model):
    "Templates for sending email"
    _name = "template.simple"
    _description = 'Templates Simple'
    _order = 'name'

    name = fields.Char('Name', required=True)
    body = fields.Html('Body', translate=True, sanitize=False)
