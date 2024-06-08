Matrix widget
=============

Matrix widget is mostly used on compute Text fileds. Like this:

.. code-block:: python

   hour_summary = fields.Text('Summary', compute='_compute_hour_summary')

on form view just add widget parameter to field:

.. code-block:: xml

    <field name="hour_summary" widget="kw_matrix_widget"/>

The most difficult stage is calculating correct json.

.. code-block:: json

    {
        "class": "table",
        "header": {"trs": [{"tds": [{"value": "Title"}]}]},
        "body": {"trs": [{"tds": [ {"value": "Value"}]}]},
        "footer": {"trs": [{"tds": [ {"value": "Footer"}]}]}
    }

You will get something like this

.. table::

    +--------+
    | Title  |
    +========+
    | Value  |
    +--------+
    | Footer |
    +--------+

Any section is not required. "header" and "footer" generation "th" html
tags for cells. "body" generate "td" html tags. Does not matter order of
this sections in json, they will be placed in order header - body - footer.
Default value for "class" is "table table-striped table-hover"

Each section (except "class". "class" is simple string) is a dictionary and
has same syntax with next keys:

#. trs
#. class

"trs" is required. For "header" section default value for "class" is
"thead-light". "trs" is a list of dict with next keys:

#. tds

"tds" is required. "tds" is a list of dict with next keys:

#. class
#. style
#. data
#. colspan
#. rowspan
#. value

"value" is required. "value" is simple string. "class", "style", "colspan",
"rowspan" will be put as param of html tag td/th. "value" will be put inside.
"data" will be put in tag param named "data-matrix". This param will
be parced for cells that has class "clickable_matrix_cell" and must contains
json with action (will be transmitted as param to ``do_action`` method)

How to prepare "data"
"""""""""""""""""""""

You should create action dict, convert it to json and base64. Like next:

.. code-block:: python

    data = {
        'name': _('Register reservation'),
        'view_mode': 'form',
        'res_model': 'kw.matrix.reserve.wizard',
        'type': 'ir.actions.act_window',
        'views': [(self.env.ref(
            'kw_equipment_rental.'
            'kw_equipment_rental_kw_matrix_reserve_wizard_form'
            '').id, 'form')],
        'context': {
            'default_kw_equipment_id': equipment_id.id,
            'default_kw_location_id': self.location_id.id,
            'default_hour': hour,
            'default_date':
                self.reservation_date.strftime('%Y-%m-%d'),
        }}
    data = json.dumps(data)
    data = base64.b64encode(data.encode()).decode()


Methods
"""""""

It maybe complicate to create multi-level json.

Abstract model *kw.matrix.compute.mixin* has methods for makes this process
easier.

.. code-block:: python

    @staticmethod
    def kw_generate_matrix_json(matrix_value,
                                col_class='align-middle text-center',
                                row_class='font-weight-bold',
                                cell_class='text-right pr-1',
                                table_class='table table-striped table-hover',
                                header_class='thead-light', ):

"matrix_value" is list of list (cells inside rows). Of course you can't use
colspan and rowspan function, but you can easy add class value to correct cell.

.. code-block:: python

    @staticmethod
        @staticmethod
    def kw_generate_matrix_value(value_list, row_names=None, col_names=None):

"value_list" is dict of dicts. "row_names" and "col_names" is a lists.
result will be list of lists. Values will be get from value_list by
"row_names" and "col_names" values.
