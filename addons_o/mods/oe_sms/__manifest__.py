# -*- coding: utf-8 -*-

{
    'name': 'Custom SMS',
    'version': '11.0.0',
    'category': 'Tools',
    'summary': 'Modification of orginal "SMS" module.',
    'description': """
This module gives a framework for SMS text messaging
----------------------------------------------------

The service is provided by the In App Odoo platform.
    """,
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://app.ecuaon.com',
    'license': 'LGPL-3',
    'depends': [
        'sms',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        #'data/installment_data.xml',
        
        # report
        
        # wizard
        #'wizard/sale_massive_products_views.xml',
        
        # views
        'views/sms_template_message_views.xml',
        
        # wizard
        'wizard/send_sms_views.xml',
        
        
        # static
        #'views/assets.xml',

        # security
        'security/ir.model.access.csv',
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