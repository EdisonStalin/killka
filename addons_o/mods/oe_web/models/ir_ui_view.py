# -*- coding: utf-8 -*-

from odoo import api, models


class View(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def render_template(self, template, values=None, engine='ir.qweb'):
        
        if template in ['web.login', 'web.webclient_bootstrap']:
            if not values:
                values = {}
            if 'uid' in self._context:
                values["title"] = self.env.user.company_id.name_software
        return super(View, self).render_template(template, values=values, engine=engine)
