# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import timedelta, datetime
from odoo.exceptions import AccessError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    requisition_id = fields.Many2one(related="order_id.requisition_id", store=True)
    cost = fields.Float(related="product_id.standard_price", group_operator="avg", store=True)
    price_gap = fields.Float(string="Variation (%)", compute="_compute_price_gap", group_operator="min", store=True)
    price_unit = fields.Float(group_operator="min")
    requisition_selected = fields.Boolean(string="Selected", default=False)

    @api.depends('cost', 'price_unit')
    def _compute_price_gap(self):
        for line in self:
            if line.cost:
                line.price_gap = (line.price_unit - line.cost) / line.cost * 100
            else:
                line.price_gap = 0

