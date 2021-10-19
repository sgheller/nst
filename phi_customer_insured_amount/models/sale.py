# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    customer_insured_amount = fields.Float("Insured amount", compute='_compute_customer_insured_amount')

    def _compute_customer_insured_amount(self):
        for order in self:
            order.customer_insured_amount = order.partner_id.customer_insured_amount or order.partner_id.parent_id.customer_insured_amount
