# -*- coding: utf-8 -*-

{
    'name': "Stock Picking From Invoice",
    'summary': """Stock Picking From Customer/Supplier Invoice""",
    'description': """This Module Enables To Create Stocks Picking From Customer/Supplier Invoice""",
    'category': 'Accounting',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://ecuaon.com',
    'license': 'LGPL-3',
    'depends': [
        'oe_account', 
        'oe_stock',
    ],
    'data': [
        
        # security
        'security/invoice_stock_security.xml',
        #'security/ir.model.access.csv',
        
        # view
        'views/account_invoice_stock_move_view.xml',
    ],
    'images': [
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
