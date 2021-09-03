# -*- coding: utf-8 -*-
{
    'name': "Phidias : Sale Payment Method",

    'summary': """
        Phidias : Sale Payment Method
        """,

    'description': """
        Phidias : Sale Payment Method
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'sale',
        'account',
    ],
    "data": [
        'views/sale_order_views.xml',
        'views/partner_view.xml',
        'views/account_invoice.xml',
    ]
}
