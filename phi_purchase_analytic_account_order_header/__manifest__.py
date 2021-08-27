# -*- coding: utf-8 -*-
{
    'name': "Phidias : Analytic account in purchase order header",

    'summary': """
        Phidias : Analytic account in purchase order header
        """,

    'description': """
        Phidias : Analytic account in purchase order header
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'account',
        'purchase',
        'account_accountant',
        'analytic',
        'analytic_enterprise',
    ],
    "data": [
        'views/purchase_order.xml',
    ]
}
