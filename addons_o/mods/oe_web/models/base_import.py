# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import UserError


class BaseImport(models.TransientModel):
    _inherit = 'base_import.import'

    def do(self, fields, options, dryrun=False):
        """
        Catch UserError exception and pass it as an error.
        Re-raise all other errors
        """
        try:
            ret = super(BaseImport, self).do(fields, options, dryrun=dryrun)
        except UserError as e:
            ret = {'messages': [{'record': False, 'type': 'warning', 'message': e.name, }]}
        except Exception:
            raise
        return ret