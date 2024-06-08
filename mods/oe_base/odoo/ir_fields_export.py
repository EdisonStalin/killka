# -*- coding: utf-8 -*-

import logging

from odoo import models, api, fields, _
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


class IrFieldExport(models.Model):
    _name = "ir.field.export"
    _description = "Field export"
    
    res_model = fields.Char('Resource Model', readonly=True, help="The database object this attachment will be attached to.")
    res_id = fields.Integer('Resource ID', readonly=True, help="The record id this is attached to.")
    ttype = fields.Selection(selection=[('sequence', 'Sequence'),
                                        ('python', 'Python'),
                                        ('value', 'Value')], default='field', required=True)
    name = fields.Char(string='Header', required=True)
    value = fields.Text(string='Value', required=True)
    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying the field.")

    @api.model
    def create(self, vals):
        res = super(IrFieldExport, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        res = super(IrFieldExport, self).write(vals)
        return res

    # TODO should add some checks on the type of result (should be char)
    @api.multi
    def _compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the environement in which to compute the rule
        :return: returns a tuple build as the base/amount computed, the quantity and the rate
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.ttype == 'value':
            try:
                return localdict.mapped(self.value)
            except:
                _logger.error(_('Wrong percentage base or quantity defined for salary rule %s (%s).') % (self.name, self.code))
        else:
            try:
                safe_eval(self.value, localdict, mode='exec', nocopy=True)
                return localdict['result']
            except:
                _logger.error(_('Wrong python code defined for salary rule %s (%s).') % (self.name, self.value))
