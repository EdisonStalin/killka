# -*- coding: utf-8 -*-

{
    'name': 'Account Custom',
    'summary': 'Modification of original "Account" module.',
    'sequence': 20,
    'category': 'Accounting',
    'version': '1.0.0',
    'author': 'Jefferson Tipan',
    'website': 'https://www.appecuaonline.net',
    'license': 'LGPL-3',
    'depends': [
        'base_import',
        'base_vat_autocomplete',
        'account',
        'account_cancel',
        'account_check_printing',
        'account_payment',
        'account_bank_statement_import',
        'oe_base',
        'oe_product',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/account_account_type_data.xml',
        'data/account_data.xml',
        'data/account_type_document.xml',
        'data/account_tax_support_data.xml',
        'data/account_method_payment_data.xml',
        'data/mail_template_data.xml',
        'data/data_partner.xml',
        'data/product_data.xml',
        'data/cron_data.xml',
        'data/exports_data.xml',
        
        #report
        'report/account_report.xml',
        'report/account_invoice_report_views.xml',
        'report/report_tax.xml',

        # views
        'views/account_view.xml',
        'views/account_template_views.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/res_users_view.xml',
        'views/account_financial_report_views.xml',
        'views/account_fiscal_position_views.xml',
        'views/account_menuitem.xml',
        'views/account_type_document_view.xml',
        'views/account_tax_support_view.xml',
        'views/account_authorization_view.xml',
        'views/account_tax_view.xml',
        'views/account_refund_invoice_view.xml',
        'views/account_invoice_view.xml',
        'views/account_withholding_view.xml',
        'views/account_purchase_clearance_view.xml',
        'views/account_payment_view.xml',
        'views/account_portal_templates.xml',
        'views/account_journal_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_bank_statement_view.xml',     

        # Wizard
        'wizard/account_invoice_refund_view.xml',
        'wizard/account_invoice_state_views.xml',
        'wizard/account_tax_wizard_views.xml',
        'wizard/import_excel_wizard.xml',

        # static
        'views/assets.xml',
        'views/account_move_views.xml',
        
        # security
        'security/account_security.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/account_reconciliation.xml',
        'static/src/xml/account_payment.xml',
    ],
    'demo': [
        #'demo/',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_auto_install_template',
}