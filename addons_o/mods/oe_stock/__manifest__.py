# -*- coding: utf-8 -*-

{
    'name': 'Module Stock Custom',
    'summary': 'Stock custom module',
    'category': 'oe',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://appecuaonline.ecuaon.com',
    'license': 'LGPL-3',

    'depends': [
        #'oe_account',
        'stock',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        #'data/',
        
        # security
        'security/stock_security.xml',
        'security/ir.model.access.csv',
        
        # report
        'report/report_stockpicking_operations.xml',
        
        # views
        'views/stock_menu_views.xml',
        'views/product_views.xml',
        'views/stock_move_views.xml',
        'views/stock_location_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_quant_views.xml',
        'views/stock_inventory_views.xml',

        # wizard
        'wizard/stock_change_product_qty_views.xml',
        'wizard/ms_report_stock_wizard.xml',

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