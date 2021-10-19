# -*- coding: utf-8 -*-
{
    'name': "Phidias : CRM Competitors",

    'summary': """
        Phidias : CRM Competitors
        """,

    'description': """
        Phidias : CRM Competitors
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
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/crm_competitor.xml',
    ]
}
