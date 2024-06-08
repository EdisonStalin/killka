# -*- coding: utf-8 -*-

{
    'name': 'Module Custom Sale',
    'version': '1.0.1',
    'category': 'Sales',
    'summary': 'Modification of orginal "Sale" module.',
    'sequence': 40,
    'description': """
This module contains all the common features of Sales Management and eCommerce.
    """,
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://app.ecuaon.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'mail',
        'oe_product',
        'sale',
        'sales_team',
        'sale_stock',
        'oe_sms',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        #'data/',
        
        # report
        'report/sale_report.xml',
        'report/sale_report_templates.xml',
        
        # wizard
        'wizard/sale_massive_products_views.xml',
        
        # views
        'views/menus.xml',
        'views/sms_template_message_views.xml',
        'views/sale_views.xml',
        'views/account_invoice_views.xml',
        'views/assets.xml',
        
        # wizard
        
        # static

        # security
        #'security/',
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