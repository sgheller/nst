
from odoo import models, fields, api, _


class CrmLead(models.Model):
    
    _inherit = 'crm.lead'

    contact_ids = fields.Many2many('res.partner', string="Others Contacts")


