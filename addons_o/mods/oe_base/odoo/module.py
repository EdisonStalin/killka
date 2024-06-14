# -*- coding: utf-8 -*-

from odoo import models, api
import odoo


class Module(models.Model):
    _inherit = 'ir.module.module'

    @api.multi
    def button_install(self):
        module_template = odoo.tools.config.options.get('module_template', False)
        if module_template:
            modules = self.search([('name', 'in', [module_template]), ('state', '=', 'uninstalled')])
            new_self = self.env['ir.module.module']
            for module in self:
                if module.name == 'l10n_ec' and modules:
                    new_self += modules
                else:
                    new_self += module
            return super(Module, new_self).button_install()
        else:
            return super(Module, self).button_install()
