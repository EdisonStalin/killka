# -*- coding: utf-8 -*-
##############################################################################
#
#    Spellbound soft solution.
#    Copyright (C) 2017-TODAY Spellbound soft solution(<http://www.spellboundss.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'POS combo Meal & Make My own Pizza',
    'category': 'point of sale',
    'author': 'Spellbound Soft Solutions',
    'version': '1.0',
    'license': 'AGPL-3',
    'website': 'www.spellboundss.com',
    'description':
        """

Odoo-10.0 Restaurant Extention module.
===============================================
        Make My Own Pizza 
        Combo Meal
""",
    'depends': ['point_of_sale'],
    'images' : ['static/description/images/banner.jpg',],
    'data': [
        'security/ir.model.access.csv',
        'security/security_group.xml',
        'views/pos_product_pack_view.xml',
        'views/pos_pack_template_view.xml',
        # 'views/pos_restaurant_view.xml',
    ],
   
    'qweb': ['static/src/xml/pos_view.xml'],
    'price':99,
    'currency':'EUR',
    'auto_install': False,
    'installable': True,

}
