# Copyright 2010-2012 Andy Lu <andy.lu@elico-corp.com> (Elico Corp)
# Copyright 2013 Agile Business Group sagl (<http://www.agilebg.com>)
# Copyright 2017 valentin vinagre  <valentin.vinagre@qubiq.es> (QubiQ)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    'name': "Phidias : Purchase quotation number",

    'summary': """
        Phidias : Purchase quotation number
        """,

    'description': """
        Phidias : Purchase quotation number
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'purchase',
    ],
    "data": [
        'views/purchase_config.xml',
        'data/data.xml',
    ]
}