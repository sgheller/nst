# -*- coding: utf-8 -*-
{
    'name': "Odoo Office 365 Connector",

    'summary': """
                Odoo Office365 Connector provides the opportunity to sync calendar, contacts, tasks and mails between ODOO and Office365.
            """,

    'description': """
    Odoo is a fully integrated suite of business modules that encompass the traditional ERP functionality. 
    Odoo office 365 Connector provides the opportunity to sync calendar, contacts,task and mail between ODOO and office 365.
    """,
    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'category': 'Connector',
    'price': 499,
    'currency': 'EUR',
    'version': '14.5.0',
    'license': 'OPL-1',
    'depends': ['base', 'calendar', 'crm'],
    'images': [
        'static/description/banner.gif',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/template.xml',
        'views/office365_sync.xml',
        'views/logging.xml',
        'views/res_partner.xml',
        'views/todo_list.xml',
        'views/calendar_event.xml',
        'views/res_settings.xml',
        'data/scheduler.xml',
        'data/general.xml',
        'data/recurring.xml',
        'wizard/message_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'live_test_url': 'https://www.youtube.com/watch?v=gvuUiAsC-TM',
}
