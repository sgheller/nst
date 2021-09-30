# -*- coding: utf-8 -*-
{
    'name': "Phidias : Customer insured amount",

    'summary': """
        Phidias : Customer insured amount
        """,

    'description': """
        Phidias : Customer insured amount
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'sale',
    ],
    "data": [
        'views/partner_view.xml',
        'views/sale_order_views.xml',
    ]
}
