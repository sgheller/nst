# -*- coding: utf-8 -*-
{
    'name': "Phidias : specifique Nexans",

    'summary': """
        Phidias : specifique Nexans
        """,

    'description': """
        Phidias : specifique Nexans
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.3',

    # any module necessary for this one to work correctly
    'depends': [
        'crm',
        'sale_management',
        'account',
        'stock',
        'project',
        'purchase',
        'account_accountant',
        'helpdesk',
        'approvals',
        'l10n_fr',
        'l10n_fr_reports',
        'l10n_fr_fec',
        'web_studio',
        'phi_analytic_account_order_from_sale_to_purchase',
        'phi_purchase_analytic_account_order_header',
        'sale_margin',
        'sales_delivery_date',
    ],
    "data": [
        'views/crm_lead_views.xml',
    ]
}
