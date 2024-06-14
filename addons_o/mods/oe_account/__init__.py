# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

from . import controllers
from . import models
from . import report
from . import wizard


def _auto_install_template(cr, registry):
    #check the country of the main company (only) and eventually load some module needed in that country
    env = api.Environment(cr, SUPERUSER_ID, {})
    #auto install localization module(s) if available
    module_rem_ids = env['ir.module.module'].search([('name', '=', 'l10n_ec'), ('state', '=', 'installed')])
    module_rem_ids.sudo().module_uninstall()
    module_list = ['oe_epd_template_super', 'base_vat']
    module_ids = env['ir.module.module'].search([('name', 'in', module_list), ('state', '=', 'uninstalled')])
    module_ids.sudo().button_install()
