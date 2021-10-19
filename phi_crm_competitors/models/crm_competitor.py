# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CrmCompetitor(models.Model):
    _name = 'phi_crm_competitors.crm.competitor'
    _description = 'Competitors'
    _order = "name"

    name = fields.Char(string="Competitor", required=True)

