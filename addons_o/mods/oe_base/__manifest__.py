# -*- coding: utf-8 -*-

{
    'name': 'Base Custom',
    'version': '1.1.0',
    'summary': 'oe modification of original "base" module.',
    'sequence': 1,
    'description': """
The kernel of Odoo, needed for all installation.
===================================================
    """,
    'category': 'Hidden',
    'author': 'Jefferson Tipan',
    'website': 'https://appecuaonline.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'decimal_precision',
        'phone_validation',
        'resource',
        'web_notify',
        'report_xlsx',
        'multi_step_wizard',
        #'base_user_role',
        #'deleted_records_info',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/identification_type_data.xml',
        'data/ir_filters.xml',
        'data/res.country.state.csv',
        'data/base_data.xml',
        'data/res_bank_data.xml',
        'data/resource_data.xml',
        
        # security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # views
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/res_bank_views.xml',
        'views/res_establishment_views.xml',
        'views/l10n_latam_identification_type_views.xml',
        'views/menus.xml',
        'views/res_users_view.xml',
        'views/decimal_precision_view.xml',
        'views/web_login.xml',
        'views/menu_secondary.xml',
        'views/web_layout.xml',
        'views/assets.xml',
        
        # ir
        'ir/ir_attachment_view.xml',
        'ir/ir_rule_view.xml',
        'ir/ir_qweb.xml',
        'ir/ir_fields_export.xml',

        # wizard
        'wizard/send_message_view.xml',

        # static
        # 'views/assets.xml',

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
    'post_load': None,
    'pre_init_hook': None,
    'post_init_hook': None,
}
