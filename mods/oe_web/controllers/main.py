# -*- coding: utf-8 -*-

import ast
import datetime
import json
import logging

import pytz

from odoo import http, tools
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.web.controllers.main import Home, ExcelExport
from odoo.http import content_disposition, request


_logger = logging.getLogger(__name__)


def set_background():
    disable_footer = False
    if request.db is not None:
        param_obj = request.env['ir.config_parameter'].sudo()
        disable_footer = param_obj.get_param('login_form_disable_footer')
    if disable_footer:
        request.params['disable_footer'] = ast.literal_eval(disable_footer) or False
        request.params['disable_database_manager'] = ast.literal_eval(
            param_obj.get_param('login_form_disable_database_manager')) or False
    else:
        return False

    change_background = ast.literal_eval(param_obj.get_param('login_form_change_background_by_hour')) or False
    if change_background:
        config_login_timezone = param_obj.get_param('login_form_change_background_timezone')
        tz = config_login_timezone and pytz.timezone(config_login_timezone) or pytz.utc
        current_hour = datetime.datetime.now(tz=tz).hour or 10

        if (current_hour >= 0 and current_hour < 3) or (current_hour >= 18 and current_hour < 24):  # Night
            request.params['background_src'] = param_obj.get_param('login_form_background_night') or ''
        elif current_hour >= 3 and current_hour < 7:  # Dawn
            request.params['background_src'] = param_obj.get_param('login_form_background_dawn') or ''
        elif current_hour >= 7 and current_hour < 16:  # Day
            request.params['background_src'] = param_obj.get_param('login_form_background_day') or ''
        else:  # Dusk
            request.params['background_src'] = param_obj.get_param('login_form_background_dusk') or ''
    else:
        request.params['background_src'] = param_obj.get_param('login_form_background_default') or ''


#----------------------------------------------------------
# Odoo Web web Controllers
#----------------------------------------------------------
class LoginHome(Home):

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        set_background()
        request.params['db_show'] = tools.config.options.get('db_show', False)
        return super(LoginHome, self).web_login(redirect, **kw)


class AuthSignupHomeInherit(AuthSignupHome):

    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        set_background()
        return super(AuthSignupHomeInherit, self).web_auth_reset_password(*args, **kw)

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        set_background()
        return super(AuthSignupHomeInherit, self).web_auth_signup(*args, **kw)


class ExcelExportView(ExcelExport):

    def __getattribute__(self, name):
        if name == 'fmt':
            raise AttributeError()
        return super(ExcelExportView, self).__getattribute__(name)

    @http.route('/web/export/xls_view', type='http', auth='user')
    def export_xls_view(self, data, token):
        data = json.loads(data)
        model = data.get('model', [])
        columns_headers = data.get('headers', [])
        rows = data.get('rows', [])
        xlsx = self.from_data(columns_headers, rows)
        report_name = self.filename(model)
        xlsxhttpheaders = [
            ('Content-Type', 'application/vnd.openxmlformats-'
                             'officedocument.spreadsheetml.sheet'),
            ('Content-Length', len(xlsx)),
            (
                'Content-Disposition',
                content_disposition(report_name + '.xlsx')
            )
        ]
        return request.make_response(xlsx, headers=xlsxhttpheaders, cookies={'fileToken': token})
