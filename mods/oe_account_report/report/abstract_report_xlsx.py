# -*- coding: utf-8 -*-

from odoo import models


class AbstractReportXslx(models.AbstractModel):
    _name = "report.account_financial_report.abstract_report_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def __init__(self, pool, cr):
        self.format_right_bold_italic = None
        self.format_bold = None
        self.format_percent_bold_italic = None


    def get_workbook_options(self):
        return {'constant_memory': True}

    def generate_xlsx_report(self, workbook, data, objects):
        report = objects

        self.row_pos = 0

        self._define_formats(workbook)

        report_name = self._get_report_name(report)
        report_footer = self._get_report_footer()
        filters = self._get_report_filters(report)
        self.columns = self._get_report_columns(report)
        self.workbook = workbook
        self.sheet = workbook.add_worksheet(report_name[:31])

        self._set_column_width()

        self._write_report_title(report_name)

        self._write_filters(filters)

        self._generate_report_content(workbook, report)

        self._write_report_footer(report_footer)


    def _write_report_footer(self, footer):
        """Write report footer .
        Columns are defined with `_get_report_columns` method.
        """
        if footer:
            self.row_pos += 1
            self.sheet.merge_range(
                self.row_pos, 0, self.row_pos, len(self.columns) - 1,
                footer, self.format_left
            )
            self.row_pos += 1


    def _write_filters(self, filters):
        """Write one line per filters on starting on current line.
        Columns number for filter name is defined
        with `_get_col_count_filter_name` method.
        Columns number for filter value is define
        with `_get_col_count_filter_value` method.
        """
        col_name = 1
        col_count_filter_name = self._get_col_count_filter_name()
        col_count_filter_value = self._get_col_count_filter_value()
        col_value = col_name + col_count_filter_name + 1
        for title, value in filters:
            self.sheet.merge_range(
                self.row_pos, col_name,
                self.row_pos, col_name + col_count_filter_name - 1,
                title, self.format_header_left)
            self.sheet.merge_range(
                self.row_pos, col_value,
                self.row_pos, col_value + col_count_filter_value - 1,
                value)
            self.row_pos += 1
        self.row_pos += 2

    def write_array_title(self, title):
        """Write array title on current line using all defined columns width.
        Columns are defined with `_get_report_columns` method.
        """
        self.sheet.merge_range(
            self.row_pos, 0, self.row_pos, len(self.columns) - 1,
            title, self.format_bold
        )
        self.row_pos += 1


    def write_initial_balance(self, my_object, label):
        """Write a specific initial balance line on current line
        using defined columns field_initial_balance name.

        Columns are defined with `_get_report_columns` method.
        """
        col_pos_label = self._get_col_pos_initial_balance_label()
        self.sheet.write(self.row_pos, col_pos_label, label, self.format_right)
        for col_pos, column in self.columns.items():
            if column.get('field_initial_balance'):
                value = getattr(my_object, column['field_initial_balance'])
                cell_type = column.get('type', 'string')
                if cell_type == 'string':
                    self.sheet.write_string(self.row_pos, col_pos, value or '')
                elif cell_type == 'amount':
                    self.sheet.write_number(
                        self.row_pos, col_pos, float(value), self.format_amount
                    )
                elif cell_type == 'amount_currency':
                    if my_object.currency_id:
                        format_amt = self._get_currency_amt_format(
                            my_object)
                        self.sheet.write_number(
                            self.row_pos, col_pos,
                            float(value), format_amt
                        )
            elif column.get('field_currency_balance'):
                value = getattr(my_object, column['field_currency_balance'])
                cell_type = column.get('type', 'string')
                if cell_type == 'many2one':
                    if my_object.currency_id:
                        self.sheet.write_string(
                            self.row_pos, col_pos,
                            value.name or '',
                            self.format_right
                        )
        self.row_pos += 1

    def write_ending_balance(self, my_object, name, label):
        """Write a specific ending balance line on current line
        using defined columns field_final_balance name.

        Columns are defined with `_get_report_columns` method.
        """
        for i in range(0, len(self.columns)):
            self.sheet.write(self.row_pos, i, '', self.format_header_right)
        row_count_name = self._get_col_count_final_balance_name()
        col_pos_label = self._get_col_pos_final_balance_label()
        self.sheet.merge_range(
            self.row_pos, 0, self.row_pos, row_count_name - 1, name,
            self.format_header_left
        )
        self.sheet.write(self.row_pos, col_pos_label, label,
                         self.format_header_right)
        for col_pos, column in self.columns.items():
            if column.get('field_final_balance'):
                value = getattr(my_object, column['field_final_balance'])
                cell_type = column.get('type', 'string')
                if cell_type == 'string':
                    self.sheet.write_string(self.row_pos, col_pos, value or '',
                                            self.format_header_right)
                elif cell_type == 'amount':
                    self.sheet.write_number(
                        self.row_pos, col_pos, float(value),
                        self.format_header_amount
                    )
                elif cell_type == 'amount_currency':
                    if my_object.currency_id:
                        format_amt = self._get_currency_amt_header_format(
                            my_object)
                        self.sheet.write_number(
                            self.row_pos, col_pos, float(value),
                            format_amt
                        )
            elif column.get('field_currency_balance'):
                value = getattr(my_object, column['field_currency_balance'])
                cell_type = column.get('type', 'string')
                if cell_type == 'many2one':
                    if my_object.currency_id:
                        self.sheet.write_string(
                            self.row_pos, col_pos,
                            value.name or '',
                            self.format_header_right
                        )
        self.row_pos += 1

    def _get_currency_amt_format(self, line_object):
        """ Return amount format specific for each currency. """
        if hasattr(line_object, 'account_group_id') and \
                line_object.account_group_id:
            format_amt = getattr(self, 'format_amount_bold')
            field_prefix = 'format_amount_bold'
        else:
            format_amt = getattr(self, 'format_amount')
            field_prefix = 'format_amount'
        if line_object.currency_id:
            field_name = \
                '%s_%s' % (field_prefix, line_object.currency_id.name)
            if hasattr(self, field_name):
                format_amt = getattr(self, field_name)
            else:
                format_amt = self.workbook.add_format()
                setattr(self, 'field_name', format_amt)
                format_amount = \
                    '#,##0.' + ('0' * line_object.currency_id.decimal_places)
                format_amt.set_num_format(format_amount)
        return format_amt

    def _get_currency_amt_header_format(self, line_object):
        """ Return amount header format for each currency. """
        format_amt = getattr(self, 'format_header_amount')
        if line_object.currency_id:
            field_name = \
                'format_header_amount_%s' % line_object.currency_id.name
            if hasattr(self, field_name):
                format_amt = getattr(self, field_name)
            else:
                format_amt = self.workbook.add_format(
                    {'bold': True,
                     'border': True,
                     'bg_color': '#FFFFCC'})
                setattr(self, 'field_name', format_amt)
                format_amount = \
                    '#,##0.' + ('0' * line_object.currency_id.decimal_places)
                format_amt.set_num_format(format_amount)
        return format_amt


    def _get_report_complete_name(self, report, prefix):
        if report.company_id:
            suffix = ' - %s - %s' % (
                report.company_id.name, report.company_id.currency_id.name)
            return prefix + suffix
        return prefix

    def _get_report_name(self, report):
        """
            Allow to define the report name.
            Report name will be used as sheet name and as report title.

            :return: the report name
        """
        raise NotImplementedError()

    def _get_report_footer(self):
        """
            Allow to define the report footer.
            :return: the report footer
        """
        return False


    def _get_report_filters(self, report):
        """
            :return: the report filters as list

            :Example:

            [
                ['first_filter_name', 'first_filter_value'],
                ['second_filter_name', 'second_filter_value']
            ]
        """
        raise NotImplementedError()

    def _get_col_count_filter_name(self):
        """
            :return: the columns number used for filter names.
        """
        raise NotImplementedError()

    def _get_col_count_filter_value(self):
        """
            :return: the columns number used for filter values.
        """
        raise NotImplementedError()

    def _get_col_pos_initial_balance_label(self):
        """
            :return: the columns position used for initial balance label.
        """
        raise NotImplementedError()

    def _get_col_count_final_balance_name(self):
        """
            :return: the columns number used for final balance name.
        """
        raise NotImplementedError()

    def _get_col_pos_final_balance_label(self):
        """
            :return: the columns position used for final balance label.
        """
        raise NotImplementedError()
