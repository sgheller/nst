# -*- coding: utf-8 -*-
{
    'name': "Phidias : Purchase supplier info quantity multiple",

    'summary': """
        Purchase supplier info quantity multiple
        """,

    'description': """
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Purchases',
    'version': '13.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['purchase_stock'],

    # always loaded
    'data': [
        'views/purchase_supplierinfo.xml',
    ],
}
