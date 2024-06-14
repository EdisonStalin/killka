# -*- coding: utf-8 -*-

{
    'name': 'Module Stock Account Custom',
    'summary': 'Stock custom module',
    'category': 'oe',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://appecuaonline.ecuaon.com',
    'license': 'LGPL-3',

    'depends': [
        'stock_account',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/stock_data.xml',
        
        # security
        #'security/stock_security.xml',
        #'security/ir.model.access.csv',
        
        # report
        #'report/report_.xml',
        
        # views
        'views/product_views.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_views.xml',

        # wizard
        #'wizard/.xml',

        # static
        #'views/assets.xml',
    ],
    'qweb': [
        #'static/src/xml/',
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