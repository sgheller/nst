# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    quadra_export_group_lines = fields.Boolean("Quadra Export Group Lines", related='company_id.quadra_export_group_lines', readonly=False)
