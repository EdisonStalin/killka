# -*- coding: utf-8 -*-

{
    'name': 'POS Restaurant Custom',
    'summary': 'Modification of original "Point of Sale" module.',
    'category': 'Point of Sale',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://ecuaon.com',
    'license': 'LGPL-3',

    'depends': [
        # Odoo
        'pos_restaurant',
        'pos_restaurant_base',
        
        # Comunity
        
        # Custom
        'oe_pos',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        #'data/general_data.xml',
        
        # views
        #'views/pos_templates.xml',
        
        # report
        #'report/pos_session_report_template.xml',
        
        # static
        'views/pos_restaurant_templates.xml',
        'views/pos_printer_views.xml',

        # security
        # 'security/',
    ],
    'qweb': [
        'static/src/xml/multiprint.xml',
    ],
    'demo': [
        #'demo/',
    ],

    'post_load': None,
    'pre_init_hook': None,
    'post_init_hook': None,

    'auto_install': False,
    'installable': True,
}