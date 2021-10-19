# -*- coding: utf-8 -*-
{
    'name': "Phidias : Incoterm Description",

    'summary': """
        Phidias : Incoterm Description
        """,

    'description': """
        Phidias : Incoterm Description
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'account',
        'purchase',
        'sale_management',
        'sale_stock',
    ],
    "data": [
        'views/sale_order_views.xml',
        'report/sale_order_report_templates.xml',
        'views/account_invoice_view.xml',
    ]
}
