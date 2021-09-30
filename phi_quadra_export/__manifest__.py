{''
 'name': 'Quadra Export',
 'summary': 'Export des écritures comptables vers QUADRATUS',
 'author': 'Auneor Conseil, Phidias',
 'website': 'http://www.phidias.fr',
 'category': 'Accounting', 'version': '0.1',
 'depends': ['account'],
 'data': [
     'views/res_config_settings_views.xml',
     'views/res_partner_views.xml',
     'wizard/export_ascii_views.xml',
     'security/ir.model.access.csv',
 ],
 'license': 'Other proprietary',
 'images': ['static/description/banner.png'],
 "cloc_exclude": [
     "**/*",  # exclude all
 ]
 }