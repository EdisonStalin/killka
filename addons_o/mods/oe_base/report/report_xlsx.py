# -*- coding: utf-8 -*-
import logging

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


class ReportHrPayslip(models.AbstractModel):
    _inherit = "report.report_xlsx.abstract"
    
    def __init__(self, pool, cr):
        # main sheet which will contains report
        self.sheet = None
        # columns of the report
        self.columns = None
        # row_pos must be incremented at each writing lines
        self.row_pos = None
        # Formats
        self.format_header_left = None
        self.format_header_center = None
        self.format_header_right = None
        self.format_header_amount = None
        self.format_right = None
        self.format_left = None
        self.format_amount = None
        self.format_percent = None

    ####################################################
    # Method Style Defined
    ####################################################

    def _define_formats(self, workbook):
        """ Add cell formats to current workbook.
        Those formats can be used on all cell.

        Available formats are :
         * format_bold
         * format_right
         * format_right_bold_italic
         * format_header_left
         * format_header_center
         * format_header_right
         * format_header_amount
         * format_amount
         * format_percent_bold_italic
        """
        self.format_bold = workbook.add_format({'bold': True})
        self.format_right = workbook.add_format({'align': 'right'})
        self.format_left = workbook.add_format({'align': 'left'})
        self.format_right_bold_italic = workbook.add_format(
            {'align': 'right', 'bold': True, 'italic': True}
        )
        self.format_header_left = workbook.add_format(
            {'bold': True,
             'border': True,
             'bg_color': '#FFFFCC'})
        self.format_header_center = workbook.add_format(
            {'bold': True,
             'align': 'center',
             'border': True,
             'bg_color': '#FFFFCC'})
        self.format_header_right = workbook.add_format(
            {'bold': True,
             'align': 'right',
             'border': True,
             'bg_color': '#FFFFCC'})
        self.format_header_amount = workbook.add_format(
            {'bold': True,
             'border': True,
             'bg_color': '#FFFFCC'})
        currency_id = self.env['res.company']._get_user_currency()
        self.format_header_amount.set_num_format('#,##0.' + '0' * currency_id.decimal_places)
        self.format_amount = workbook.add_format()
        self.format_amount.set_num_format('#,##0.' + '0' * currency_id.decimal_places)
        self.format_amount_bold = workbook.add_format({'bold': True})
        self.format_amount_bold.set_num_format('#,##0.' + '0' * currency_id.decimal_places)
        self.format_percent_bold_italic = workbook.add_format({'bold': True, 'italic': True})
        self.format_percent_bold_italic.set_num_format('#,##0.00%')

    ####################################################
    # Methods for content
    ####################################################

    def _write_report_title(self, title):
        """Write report title on current line using all defined columns width.
        Columns are defined with `_get_report_columns` method.
        """
        self.sheet.merge_range(self.row_pos, 0, self.row_pos, len(self.columns) - 1, title, self.format_bold)
        self.row_pos += 3

    def _generate_report_content(self, workbook, report):
        """
            Allow to fetch report content to be displayed.
        """
        raise NotImplementedError()

    # TODO should add some checks on the type of result (should be char)
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
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).') % (self.name, self.code))
        else:
            try:
                safe_eval(self.value, localdict, mode='exec', nocopy=True)
                return localdict['result']
            except:
                raise UserError(_('Wrong python code defined for expression %s (%s).') % (self.name, self.value))

    def write_line(self, line_object):
        """Write a line on current line using all defined columns field name.
        Columns are defined with `_get_report_columns` method.
        """
        try:
            for col_pos, column in self.columns.items():
                cell_type = column.get('type', 'string')
                if cell_type == 'python':
                    value = column.get('value', False)
                    self.sheet.write_string(self.row_pos, col_pos, value or '')
                else:
                    value = getattr(line_object, column['field'])
                    if cell_type == 'many2one':
                        if 'sub_field' in column:
                            value = getattr(value, column['sub_field'])
                            cell_type = column.get('sub_type', 'string')
                            if cell_type == 'many2one' and 'sub_value' in column:
                                value = getattr(value, column['sub_value'])
                                cell_type = column.get('value_type', 'string')
                            self._write_line(line_object, cell_type, col_pos, value, column)
                        else:
                            self._write_line(line_object, cell_type, col_pos, value)
                    elif cell_type == 'one2many':
                        value = value.filtered(lambda l: getattr(l, column['sub_field']) == column['value_search']).mapped(column['sub_value'])
                        if type(value) == list:
                            value = value[0] if len(value) else 0.0
                        cell_type = column.get('sub_type', 'string')
                        self._write_line(line_object, cell_type, col_pos, value)
                    else:
                        self._write_line(line_object, cell_type, col_pos, value)
        except Exception as e:
            _logger.error(_('Not finding record path %s, error: %s') % (column, e))
            return False
        self.row_pos += 1
        return True

    def _write_line(self, line_object, cell_type, col_pos, value, column={}):
        try:
            if cell_type == 'many2one':
                self.sheet.write_string(self.row_pos, col_pos, value.name or '', self.format_right)
            elif cell_type == 'string':
                if hasattr(line_object, 'account_group_id') and line_object.account_group_id:
                    self.sheet.write_string(self.row_pos, col_pos, value or '', self.format_bold)
                else:
                    self.sheet.write_string(self.row_pos, col_pos, value or '')
            elif cell_type == 'amount':
                if hasattr(line_object, 'account_group_id') and line_object.account_group_id:
                    cell_format = self.format_amount_bold
                else:
                    cell_format = self.format_amount
                value = float('{:.2f}'.format(value))
                self.sheet.write_number(self.row_pos, col_pos, value or 0.0, cell_format)
            elif cell_type == 'amount_currency':
                if line_object.currency_id:
                    format_amt = self._get_currency_amt_format(line_object)
                    value = float('{:.2f}'.format(value))
                    self.sheet.write_number(self.row_pos, col_pos, value or 0.0, format_amt)
            elif cell_type == 'selection':
                record = getattr(line_object.with_context({'lang': self.env.user.lang}), column['field'])
                field = record._fields[column['sub_field']]
                value = field.convert_to_export(value, record)
                self.sheet.write_string(self.row_pos, col_pos, value or '')
        except Exception as e:
            _logger.error(_('Not finding record path %s, error: %s') % (value, e))

    ####################################################
    # Methods for columns
    ####################################################

    def _get_report_columns(self, report):
        """
            Allow to define the report columns
            which will be used to generate report.
            :return: the report columns as dict
            :Example:

            {
                0: {'header': 'Simple column',
                    'field': 'field_name_on_my_object',
                    'width': 11},
                1: {'header': 'Amount column',
                     'field': 'field_name_on_my_object',
                     'type': 'amount',
                     'width': 14},
            }
        """
        raise NotImplementedError()

    def _set_column_width(self):
        """Set width for all defined columns.
        Columns are defined with `_get_report_columns` method.
        """
        for position, column in self.columns.items():
            self.sheet.set_column(position, position, column['width'])

    def write_array_header(self):
        """Write array header on current line using all defined columns name.
        Columns are defined with `_get_report_columns` method.
        """
        for col_pos, column in self.columns.items():
            self.sheet.write(self.row_pos, col_pos, column['header'], self.format_header_center)
        self.row_pos += 1
        
