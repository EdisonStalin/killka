# -*- coding: utf-8 -*-

{
    'name': 'SRI Statement',
    'summary': 'Tax return to SRI module.',
    'category': 'Accounting',
    'version': '1.0.0',
    'author': 'Jefferson Tipan',
    'website': 'https://www.appecuaonline.net',
    'license': 'LGPL-3',
    'depends': [
        'oe_account',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/statement_line_data.xml',
        'data/statement_line_103_data.xml',
        
        # security
        'security/statement_security.xml',
        'security/ir.model.access.csv',
        
        #report
        #'report/report_account_xlsx.xml',

        
        # views
        'views/statement_menuitem.xml',
        'views/ats_statement_views.xml',
        'views/statement_form_settings_views.xml',
        #'views/account_account_views.xml',
        #'views/account_move_views.xml',

        # Wizard
        #'wizard/'

        # static
        #'views/assets.xml',

    ],
    'qweb': [
        #'static/src/xml/account_reconciliation.xml',
    ],
    'demo': [
        #'demo/',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': False,
}