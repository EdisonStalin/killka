# -*- coding: utf-8 -*-

{
    'name': 'Purchase Requisition Custom',
    'summary': 'Modification of original "Purchase Requisition" module.',
    'category': 'Purchases',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://ecuaon.com',
    'license': 'LGPL-3',
    'sequence': 63,
    'depends': [
        'purchase_requisition',
        'oe_purchase',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        #'data/_data.xml',
        
        # views
        'views/purchase_requisition_views.xml',
        
        # report
        'report/report_purchaserequisition.xml',
        
        # static
        #'views/.xml',

        # security
        # 'security/',
    ],
    'qweb': [
        #'static/src/xml/.xml',
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