# -*- coding: utf-8 -*-
{
    'name': "Phidias : Requisition from sale order",

    'summary': """
        Phidias : Requisition from sale order
        """,

    'description': """
        Phidias : Requisition from sale order
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.3',

    # any module necessary for this one to work correctly
    'depends': [
        'purchase',
        'sale',
        'purchase_requisition',
        'phi_product_last_purchase_info',
    ],
    "data": [
        'views/sale_order_views.xml',
        'views/purchase_requisition_views.xml',
        'wizard/sale_requisition_generate_view.xml',
        'security/ir.model.access.csv',
        'wizard/purchase_requisition_add_products.xml',
    ]
}
