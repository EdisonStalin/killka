# -*- coding: utf-8 -*-

{
    'name': 'Web Custom',
    'version': '11.1.0',
    'summary': 'oe modification of original "Web" module.',
    'sequence': 2,
    'description': """
Odoo Web core module.
========================

This module provides the core of the Odoo Web Client.
    """,
    'category': 'Hidden',
    'author': 'Jefferson Tipan',
    'website': 'https://appecuaonline.com',
    'license': 'LGPL-3',
    'depends': [
        # Odoo
        
        'base_import',
        'document',
        'iap',
        'web',
        'web_editor',
        
        # Comunity Odoo
        'web_widget_x2many_2d_matrix',
        'kw_matrix_widget',
        
        'oe_base',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/ir_config_parameter.xml',
        
        # views
        # 'views/.xml',

        # static
        'views/assets.xml',
        'views/report_templates.xml',

        # security
        'security/security.xml',
    ],
    'qweb': [
        'static/src/xml/dashboard.xml',
        'static/src/xml/web_export_template_view.xml',
        'static/src/xml/listview_button_view.xml',
        'static/src/xml/button_import.xml',
        'static/src/xml/datepicker.xml',
        'static/src/xml/progress_bar.xml',
        'static/src/xml/web_progress_menu.xml',
    ],
    'demo': [
        # 'demo/',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_load': None,
    'pre_init_hook': None,
    'post_init_hook': None,
}
