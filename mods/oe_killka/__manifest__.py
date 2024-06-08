# -*- coding: utf-8 -*-

{
    'name': 'Module Custom Killka',
    'summary': 'oe modification module for Killka.',
    'category': 'oe',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://oe.systems',
    'license': 'LGPL-3',

    'depends': [
        'oe_base',
        'oe_web',
        'account',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/base_data.xml',
        'data/ir_config_parameter.xml',
        
        # views
        #'views/menuitem.xml',

        # static
        #'views/assets.xml',

        # security
        #'security/',
    ],
    'qweb': [
        'static/src/xml/dashboard.xml',
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