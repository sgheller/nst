# -*- coding: utf-8 -*-
{
    'name': "Phidias : CRM Lead Others contacts",

    'summary': """
        Phidias : CRM Lead Others contacts
        """,

    'description': """
        Phidias : CRM Lead Others contacts
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'crm',
    ],
    "data": [
        'views/crm_lead_views.xml',
    ]
}
