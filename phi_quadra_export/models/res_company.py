# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    quadra_export_group_lines = fields.Boolean("Quadra Export Group Lines")
