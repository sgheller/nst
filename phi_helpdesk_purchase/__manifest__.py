# -*- coding: utf-8 -*-
{
    'name': "Phidias : Helpdesk Purchase",

    'summary': """
        Phidias : Helpdesk Purchase
        """,

    'description': """
        Phidias : Helpdesk Purchase
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'helpdesk_sale',
        'purchase',
    ],
    "data": [
        'views/purchase_order_views.xml',
        'views/helpdesk_views.xml',
    ]
}
