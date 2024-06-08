# -*- coding: utf-8 -*-

{
    'name': 'Account Reporting Custom',
    'summary': 'Modification of original "Account" module.',
    'sequence': 20,
    'category': 'Accounting',
    'version': '1.0.0',
    'author': 'Jefferson Tipan',
    'website': 'https://www.appecuaonline.net',
    'license': 'LGPL-3',
    'depends': [
        'oe_account',
        #'report_xlsx',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        #'data/account_account_type_data.xml',
        
        #report
        'report/account_report_payment_receipt_templates.xml',
        'report/account_report_move.xml',
        'report/account_report_general_ledger.xml',
        'report/account_report_journal_ledger.xml',
        'report/account_report_aged_partner_balance.xml',
        'report/account_check_report.xml',
        'report/account_report_vat_view.xml',
        'report/customer_outstading_statement.xml',
        'report/report_account.xml',
        'report/report_account_web.xml',
        'report/report_account_xlsx.xml',
        'report/layouts.xml',
        'report/report_account_check_bank.xml',
        'report/report_tax.xml',
        'report/report_statement.xml',
        
        
        # views
        'views/report_account_state.xml',
        'views/account_report.xml',
        'views/account_statement_report.xml',
        'views/assets.xml',

        # Wizard
        'wizard/account_financial_report_view.xml',
        'wizard/account_report_complementary_view.xml',
        'wizard/customer_outstanding_statement_views.xml',
        'wizard/account_report_general_ledger_view.xml',
        'wizard/account_report_trial_balance_view.xml',
        'wizard/account_report_print_journal_view.xml',
        'wizard/account_report_tax_view.xml',
        'wizard/account_report_aged_partner_balance_view.xml',
        'wizard/account_report_file_view.xml',

        # static
        #'views/account.xml',

        # security
        #'security/account_security.xml',
        #'security/ir.model.access.csv',
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