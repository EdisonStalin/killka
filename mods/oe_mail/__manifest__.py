# -*- coding: utf-8 -*-

{
    'name': 'Custom Module Mail',
    'summary': 'Modification of original "mail" module.',
    'category': 'oe',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://ecuaon.com',
    'license': 'LGPL-3',

    'depends': [
        'mail',
        'calendar',
        'oe_base',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/mail_data.xml',
        
        # views
        'views/menus.xml',
        'views/calendar_views.xml',
        'views/mail_activity_views.xml',
        'views/res_users_views.xml',
        'views/mail_templates.xml',
        'views/mail_mail_views.xml',
        'views/mail_template_views.xml',
        
        #wizard
        #'wizard/template_simple_view.xml',
        'wizard/mail_compose_message_view.xml',

        # static
        #'views/assets.xml',

        # security
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/systray.xml',
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