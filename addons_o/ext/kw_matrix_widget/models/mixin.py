import json
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MatrixComputeMixin(models.AbstractModel):
    _name = 'kw.matrix.compute.mixin'
    _description = 'Mixin provides methods for matrix generation'

    @staticmethod
    def kw_generate_matrix_json(matrix_value,
                                col_class='align-middle text-center',
                                row_class='font-weight-bold',
                                cell_class='text-right pr-1',
                                table_class='table table-striped table-hover',
                                header_class='thead-light', ):
        value = {'header': {'trs': [], 'class': header_class},
                 'body': {'trs': []}, 'class': table_class, }
        first_row = True
        for row in matrix_value:
            try:
                if first_row:
                    tds = []
                    for cell in row:
                        tds.append({'value': cell, 'class': col_class})
                    value['header']['trs'].append({'tds': tds})
                    first_row = False
                else:
                    first_cell = True
                    tds = []
                    for cell in row:
                        if first_cell:
                            tds.append({
                                'value': '{}'.format(cell), 'class': row_class})
                            first_cell = False
                        else:
                            tds.append({
                                'value': '{}'.format(cell), 'class': cell_class})
                    value['body']['trs'].append({'tds': tds})
            except Exception as ex:
                _logger.error(ex)
        return json.dumps(value)

    @staticmethod
    def kw_generate_matrix_value(value_list, row_names=None, col_names=None):
        if not row_names:
            row_names = [x[0] for x in value_list]
            row_names = list(set(row_names))
            row_names.sort()
        row_keys = {}
        i = 0
        for x in row_names:
            i += 1
            row_keys[x] = i
        if not col_names:
            col_names = [x[1] for x in value_list]
            col_names = list(set(col_names))
            col_names.sort()
        col_keys = {}
        i = 0
        for x in col_names:
            i += 1
            col_keys[x] = i
        values = [['', ] + [x for x in col_names]]
        for i in row_names:
            values.append([i, ] + ['' for x in col_names])
        for i in value_list:
            values[row_keys[i[0]]][col_keys[i[1]]] = i[2]
        return values
