# -*- coding: utf-8 -*-

{
    'name': 'POS Custom',
    'summary': 'Modification of original "Point of Sale" module.',
    'category': 'Point of Sale',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://ecuaon.com',
    'license': 'LGPL-3',
    'depends': [
        'oe_account',
        'point_of_sale',
        'pos_cash_rounding',
        'pos_discount',
        'product_multiple_barcodes',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/cron_data.xml',
        'data/general_data.xml',
        
        # views
        'views/product_template_views.xml',
        'views/pos_templates.xml',        
        'views/pos_config_view.xml',
        'views/pos_category_view.xml',
        'views/pos_order_view.xml',
        'views/pos_session_view.xml',
        'views/point_of_sale_dashboard.xml',
        'views/account_invoice_view.xml',
        'views/res_config_settings_views.xml',
        
        # report
        'report/pos_session_report_template.xml',
        'report/pos_report.xml',
        'report/report_saledetails.xml',
        
        # static
        'views/assets.xml',

        # security
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/pos.xml',
        'static/src/xml/pos_return.xml',
        'static/src/xml/session_lock.xml',
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