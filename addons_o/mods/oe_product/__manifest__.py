#!/usr/bin/env python3
# -*- coding: utf-8 -*-

{
    'name': 'Product Custom',
    'version': '1.1.0',
    'summary': 'Modification of orginal "Product" module.',
    'sequence': 3,
    'description': """
This is the base module for managing products and pricelists in Odoo.
========================================================================

Products support variants, different pricing methods, vendors information,
make to stock/order, different units of measure, packaging and properties.

Pricelists support:
-------------------
    * Multiple-level of discount (by product, category, quantities)
    * Compute price based on different criteria:
        * Other pricelist
        * Cost price
        * List price
        * Vendor price

Pricelists preferences by product and/or partners.

Print product labels with barcode.
    """,
    'category': 'Sales',
    'application': False,
    'author': 'Jefferson Tipan',
    'website': 'https://ecuaon.com',
    'license': 'LGPL-3',
    'depends': [
        'product',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'data': [
        # data
        'data/product_data.xml',
        
        # security
        'security/ir.model.access.csv',
        
        # views
        'views/product_category_views.xml',
        'views/product_template_view.xml',

        # static
        #'views/assets.xml',
    ],
    'qweb': [
        #'static/src/xml/',
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