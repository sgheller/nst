# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    package_nb = fields.Integer("Package #", compute="_compute_package_nb")
    sale_order_origin = fields.Char("Sale Order Origin", compute="_compute_sale_order_origin")
    commercial_invoice = fields.Char("Commercial invoice")

    def _compute_package_nb(self):
        for picking in self:
            picking.package_nb = len(picking.package_ids)

    def _compute_sale_order_origin(self):
        for picking in self:
            sale_orders = picking.purchase_id._get_sale_orders().mapped('name')
            picking.sale_order_origin = ", ".join(sale_orders)

