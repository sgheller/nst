# -*- coding: utf-8 -*-
{
    'name': "Phidias : Cash Flow",

    'summary': """
        Phidias : Cash Flow
        """,

    'description': """
        Phidias : Cash Flow
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'crm',
        'sale',
        'purchase',
        'account',
        'sale_purchase',
        'account_accountant',
        'analytic',
        'analytic_enterprise',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/analytic_views.xml',
        'views/sale_order_views.xml',
    ]
}

