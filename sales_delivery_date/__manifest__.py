# -*- coding: utf-8 -*-
{
    'name': "Sale Order Line Delivery Date",
    'version': '1.0',
    'summary': "This module allows you to manage the delivery orders by date.",
    'author': 'ErpMstar Solutions',
    'category': 'Sale',
    'sequence': 5,

    'website': '',

    'depends': ['sale', 'stock'],
    'data': [
        'views/sale_order_delivery_date_view.xml',
    ],
    'qweb': [
    ],
    'images': [
        'static/description/so_confirmed.jpg',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 15,
    'currency': 'EUR',
}
