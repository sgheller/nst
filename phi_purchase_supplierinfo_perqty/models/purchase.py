# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id:
            return
        params = {'order_id': self.order_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller:
            self.product_qty = seller.get_multiple_qty(self.product_qty)

        super(PurchaseOrderLine, self)._onchange_quantity()


class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    qty_multiple = fields.Float(
        'Par combien (PCB)', digits='Product Unit of Measure',
        default=1, required=True,
        help="The procurement quantity will be rounded up to this multiple.  If it is 0, the exact quantity will be used.")

    _sql_constraints = [
        ('qty_multiple_supplierinfo_check', 'CHECK( qty_multiple >= 0 )', 'Qty Multiple must be greater than or equal to zero.'),
    ]

    def get_multiple_qty(self, qty):
        qty_rounded = qty
        if float_compare(self.qty_multiple, 1.0, precision_rounding=self.product_uom.rounding) > 0:
            remainder = self.qty_multiple > 0 and qty % self.qty_multiple or 0.0

            if float_compare(remainder, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                qty_rounded += self.qty_multiple - remainder

            qty_rounded = float_round(qty_rounded, precision_rounding=self.product_uom.rounding)

        return qty_rounded
