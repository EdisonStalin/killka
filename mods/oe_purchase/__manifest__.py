# -*- coding: utf-8 -*-

{
    'name': 'Purchase Module',
    'summary': 'oe modification of original "Purchase" module.',
    'category': 'oe',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://www.appecuaonline.com',
    'license': 'LGPL-3',
    'sequence': 62,
    'depends': [
        'purchase',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/mail_template_data.xml',
        
        # wizard
        'wizard/purchase_massive_products_views.xml',
        
        # views
        'views/purchase_menu_views.xml',
        'views/purchase_views.xml',

        # Report
        'report/purchase_order_templates.xml',
        'report/purchase_quotation_templates.xml',

        # static
        #'views/assets.xml',

        # security
        #'security/',
    ],
    'qweb': [
        #'static/src/xml/dashboard.xml',
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