# -*- coding: utf-8 -*-

{
    'name': 'Documents Electronic',
    'summary': 'Send electronic documents to the SRI.',
    'sequence': 21,
    'category': 'oe',
    'version': '1.0.0',
    'author': 'Jefferson Tipan',
    'website': 'https://appecuaonline.net',
    'license': 'LGPL-3',

    'depends': [
        'account_invoicing',
        'oe_account',
        'oe_mail',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # security
        'security/account_security.xml',
        'security/ir.model.access.csv',
        
        # reports
        'report/report_templates.xml',
        'report/report_electronic_invoice.xml',
        'report/report_electronic_withholding.xml',
        'report/report_transport_permit.xml',
        'report/account_report.xml',
        
        # data
        'data/cron_data.xml',
        'data/mail_template_data.xml',
        'data/code_validation.xml',
        'data/account_data.xml',

        # views
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
        'views/account_invoice_view.xml',
        'views/account_withholding_view.xml',
        'views/account_purchase_clearance_view.xml',
        'views/transport_permit_view.xml',
        'views/account_portal_templates.xml',
        'views/account_journal_dashboard_views.xml',
        'views/account_menuitem.xml',
        
        # wizard
        'wizard/account_document_sent_view.xml',

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
