# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Extend kitchen receipt',
    'version': '0.1',
    'author': 'Bitodoo',
    'category': 'Tools',
    'summary': 'Extend kitchen receipt [Add date and waiter]',
    'website': 'https://www.bitodoo.com',
    'license': 'AGPL-3',
    'description': """
        Add date in pos_restaurant ticket
    """,
    'depends': ['pos_restaurant'],
    'data': ['views/pos_restaurant_templates.xml'],
    'qweb': ['static/src/xml/multiprint.xml'],
    'images': [],
    'installable': True,
    'auto_install': False,
}
