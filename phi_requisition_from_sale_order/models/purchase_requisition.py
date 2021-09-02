# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    sale_id = fields.Many2one('sale.order', 'Sale Order')

    def generate_default_purchase_orders(self):
        self.ensure_one()
        for line in self.line_ids:
            vendors = line.product_id.seller_ids.mapped('name')
            for vendor in vendors:
                purchase_order = self.purchase_ids.filtered(lambda s: s.partner_id == vendor)
                if not purchase_order:
                    purchase_order = self.env['purchase.order'].create({
                        'partner_id': vendor.id,
                        'requisition_id': self.id
                    })
                self.env['purchase.order.line'].create({
                    'order_id': purchase_order.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom': line.product_uom_id.id
                })
