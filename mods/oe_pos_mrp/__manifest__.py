# -*- coding: utf-8 -*-

{
    'name': 'Make MRP orders from POS',
    'summary': """Launch Automatic MRP Orders After Selling Through POS.""",
    'description': """Launch automatic MRP orders after selling through POS""",
    'category': 'Point Of Sale',
    'version': '1.0.0',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://ecuaon.com',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'mrp',
        'stock',
        'oe_mrp',
        'oe_pos',
    ],
    'data': [
        # security
        'security/ir.model.access.csv',
        
        # view
        'views/assets.xml',
        'views/product_view.xml',
        'views/pos_order_view.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
}
