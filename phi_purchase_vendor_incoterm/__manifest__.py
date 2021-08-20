# -*- coding: utf-8 -*-
{
    'name': "Phidias : Vendor Incoterm",

    'summary': """
        Phidias : Vendor Incoterm
        """,

    'description': """
        Phidias : Vendor Incoterm
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'purchase_stock',
        'account',
    ],
    "data": [
        'views/partner_view.xml'
    ]
}
