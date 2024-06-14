# -*- coding: utf-8 -*-

import werkzeug.utils

from odoo import http
from odoo.addons.web.controllers import main
from odoo.http import request
from odoo.tools import SUPERUSER_ID


# Debug
# admin siempre en debug mode
class Home(main.Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        req = request
        if not req.debug and req.session.uid == SUPERUSER_ID:
            return werkzeug.utils.redirect(req.httprequest.full_path + ('?' not in req.httprequest.full_path and '?' or '&') + 'debug=assets')
        return main.Home.web_client(self, s_action, **kw)
