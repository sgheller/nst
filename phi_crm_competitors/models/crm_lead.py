
from odoo import models, fields, api, _


class CrmLead(models.Model):
    
    _inherit = 'crm.lead'

    competitor_ids = fields.Many2many('phi_crm_competitors.crm.competitor', string="Competitors")


