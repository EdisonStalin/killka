# -*- coding: utf-8 -*-

from datetime import datetime
import time

import pytz

from odoo.netsvc import DBFormatter
from odoo.tools import config


def convert(self, timestamp):
    if config.options.get('timezone', False):
        return time.localtime(time.mktime(datetime.fromtimestamp(timestamp, pytz.timezone(config['timezone'])).timetuple()))
    else:
        return time.localtime(timestamp)

    
DBFormatter.converter = convert
