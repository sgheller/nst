# -*- coding: utf-8 -*-
{
    'name': "Phidias : Purchase/Sale order mail with products attachments",

    'summary': """
        Phidias : Purchase/Sale order mail with products attachments
        """,

    'description': """
        Phidias : Purchase/Sale order mail with products attachments
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'purchase',
        'mail',
        'sale'
    ],
    "data": [
        'views/mail_template_view.xml',
    ]
}
