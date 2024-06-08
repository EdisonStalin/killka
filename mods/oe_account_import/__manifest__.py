# -*- coding: utf-8 -*-

{
    'name': 'Import Documents Electronic',
    'summary': 'Modification of original "Account" module.',
    'category': 'g3',
    'version': '2.1.0',
    'application': True,
    'author': 'Jefferson Tipan',
    'website': 'https://www.appecuaonline.net',
    'license': 'LGPL-3',
    'sequence': 7,
    'depends': [
        'base_import',
        'oe_account',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        #'data/.xml',
        
        # security
        #'security/account_security.xml',
        #'security/ir.model.access.csv',
        
        #report
        #'report/.xml',

        # views
        'views/assets.xml',
        'views/import_document_wizard.xml',
        
        
        # Wizard
        #'wizard/.xml',

    ],
    'qweb': [
        'static/src/xml/base_import.xml',
    ],
    'demo': [
        #'demo/',
    ],

    'installable': True,
    'auto_install': False,
    'post_init_hook': False,
}