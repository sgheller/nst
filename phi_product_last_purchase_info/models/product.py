# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    purchase_last_date = fields.Date("Last purchase date", compute="_compute_purchase_last_info")
    purchase_last_partner_id = fields.Many2one('res.partner', 'Last purchase Vendor', compute="_compute_purchase_last_info")

    def _compute_purchase_last_info(self):
        for product in self:
            purchase_order_lines = product.purchase_order_line_ids.filtered(lambda s: s.order_id.state in ('done', 'purchase')).sorted(lambda s: s.order_id.date_approve, reverse=True)
            purchase_order_lines = purchase_order_lines.filtered(lambda s: not s.company_id or s.company_id.id == self.env.company.id)
            if len(purchase_order_lines):
                product.purchase_last_date = purchase_order_lines[0].order_id.date_approve
                product.purchase_last_partner_id = purchase_order_lines[0].partner_id
            else:
                product.purchase_last_date = False
                product.purchase_last_partner_id = False
