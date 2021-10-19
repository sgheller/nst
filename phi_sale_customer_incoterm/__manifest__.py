# -*- coding: utf-8 -*-
{
    'name': "Phidias : Customer Incoterm",

    'summary': """
        Phidias : Customer Incoterm
        """,

    'description': """
        Phidias : Customer Incoterm
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'sale_stock',
        'account',
    ],
    "data": [
        'views/partner_view.xml'
    ]
}
