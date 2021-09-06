# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin_percent = fields.Float("Margin (%)", compute='_compute_margin', inverse='_inverse_margin_percent', store=True, groups="base.group_user")

    @api.onchange('margin_percent')
    def _inverse_margin_percent(self):
        for line in self:
            if line.purchase_price:
                line.price_unit = line.purchase_price / ( 1 - line.margin_percent) if (line.margin_percent - 1) else line.purchase_price
            #line.margin = line.price_subtotal - (line.purchase_price * line.product_uom_qty)
