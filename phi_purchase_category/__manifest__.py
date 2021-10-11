# -*- coding: utf-8 -*-
{
    'name': "Phidias : Purchase Category",

    'summary': """
        Phidias : Purchase Category
        """,

    'description': """
        Phidias : Purchase Category
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.2',

    # any module necessary for this one to work correctly
    'depends': [
        'purchase',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/purchase_category.xml',
        'views/purchase_order.xml',
        'views/partner_view.xml',
    ]
}
