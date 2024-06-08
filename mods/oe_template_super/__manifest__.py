# -*- coding: utf-8 -*-

{
    'name': 'Template Super Company',
    'summary': 'Template super business',
    'category': 'Localization',
    'version': '1.0.0',
    'author': 'Jefferson Tipan',
    'website': 'https://www.appecuaonline.net',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'oe_account',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/statement_line_code_data.xml',
        'data/statement_relation_code_data.xml',
        'data/account_group.xml',
        'data/account_ec_chart_super_compania.xml',
        'data/account_tax_iva_rent.xml',
        'data/account_tax_ice.xml',
        'data/account_tax_iva.xml',
        'data/account_tax_rent_no_resident.xml',
        'data/account_tax_rent_resident.xml',
        'data/account_fiscal_position.xml',
        'data/account_chart_template_data.yml',
        
        # views
        # 'views/',

        # static
        # 'views/assets.xml',

        # security
        # 'security/',
    ],
    'qweb': [
        # 'static/src/xml/',
    ],
    'demo': [
        # 'demo/',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
