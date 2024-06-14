# -*- coding: utf-8 -*-

import logging
from os.path import exists
import re

from odoo import http
import odoo
from odoo.http import request, db_filter


_logger = logging.getLogger(__name__)


def db_filter(dbs, httprequest=None):
    domains = []
    httprequest = httprequest or request.httprequest
    h = httprequest.environ.get('HTTP_X_FORWARDED_HOST', httprequest.environ.get('HTTP_HOST', '')).split(':')[0]
    d, _, r = h.partition('.')
    r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
    dbs = [i for i in dbs if re.match(r, i)]
    #if d == "www" and r:
    #    dbs += [h]
    path_domain = odoo.tools.config.options.get('path_domains', False)
    if path_domain and exists(path_domain):
        f = open(path_domain)
        domains += [x.strip().replace(' ', '').split('=') for x in f.readlines()]
    else:
        _logger.critical("""The "path_domains" parameter is not added in the odoo.conf, for the redirection of the subdomains.""")
    for x in domains:
        if x[0] == h:
            dbs = [x[1]]
            break
    return dbs


http.db_filter = db_filter
