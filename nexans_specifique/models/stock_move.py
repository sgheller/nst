# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'


    weight_gross = fields.Float("Weight Gross", digits='Stock Weight', compute="_compute_weight_gross")

    def _compute_weight_gross(self):
        for move in self:
            move.weight_gross = sum(move.move_line_ids.mapped("weight_gross_print"))