# -*- coding: utf-8 -*-

import uuid

from odoo import models, api


class IrCron(models.Model):
    _inherit = 'ir.cron'

    @api.model
    def _callback(self, cron_name, server_action_id, job_id):
        """
        Add web progress code if it does not exist.
        This allows to report progress of cron-executed jobs
        """
        new_self = 'progress_code' in self._context and self or self.with_context(progress_code=str(uuid.uuid4()), cron=True)
        return super(IrCron, new_self)._callback(cron_name, server_action_id, job_id)
