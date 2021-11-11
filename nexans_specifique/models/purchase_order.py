# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import timedelta, datetime
from odoo.exceptions import AccessError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    product_attachment_nb = fields.Integer("Product Attachment #", compute="_compute_product_attachment_nb")

    def _compute_product_attachment_nb(self):
        for order in self:
            products = order.mapped('order_line.product_id')
            attachments = self.env['ir.attachment'].search(
                [
                    '|', '&',
                    ('res_model', 'in', ['product.product']),
                    ('res_id', 'in', products.ids),'&',('res_model', 'in', ['product.template']),
                    ('res_id', 'in', products.mapped('product_tmpl_id').ids)
                ])
            order.product_attachment_nb = len(attachments)

    def _add_supplier_to_product(self):
        # Add the partner in the supplier list of the product if the supplier is not registered for
        # this product. We limit to 10 the number of suppliers for a product to avoid the mess that
        # could be caused for some generic products ("Miscellaneous").
        for line in self.order_line:
            # Do not add a contact as a supplier
            try:
                partner = self.partner_id if not self.partner_id.parent_id else self.partner_id.parent_id
                if line.product_id and partner:
                    # Convert the price in the right currency.
                    currency = partner.property_purchase_currency_id or self.env.company.currency_id
                    price = self.currency_id._convert(line.price_unit, currency, line.company_id, line.date_order or fields.Date.today(), round=False)
                    # Compute the price for the template's UoM, because the supplier's UoM is related to that UoM.
                    if line.product_id.product_tmpl_id.uom_po_id != line.product_uom:
                        default_uom = line.product_id.product_tmpl_id.uom_po_id
                        price = line.product_uom._compute_price(price, default_uom)

                    seller = line.product_id._select_seller(
                        partner_id=partner,
                        quantity=line.product_qty,
                        uom_id=line.product_uom)

                    if seller:
                        if seller.price != price:
                            if line.product_id.purchase_price_index:
                                seller.write({'price': price})
                            else:
                                date = line.order_id.date_order and line.order_id.date_order.date()
                                if seller.date_start != date:
                                    seller.copy({
                                        'sequence': max(line.product_id.seller_ids.mapped('sequence')) + 1 if line.product_id.seller_ids else 1,
                                        'price': price,
                                        'currency_id': currency.id,
                                        'date_start': date,
                                    })
                                    seller.date_end = date - timedelta(days=1)
                                else:
                                    seller.price = price
                    else:
                        seller = line.product_id._select_seller(
                            quantity=line.product_qty,
                            uom_id=line.product_uom)
                        if seller:
                                seller.copy({
                                    'name': partner.id,
                                    'price': price,
                                })
                        else:
                            if not line.product_id.purchase_price_index:
                                supplierinfo = {
                                    'name': partner.id,
                                    'sequence': max(line.product_id.seller_ids.mapped(
                                        'sequence')) + 1 if line.product_id.seller_ids else 1,
                                    'min_qty': 0.0,
                                    'price': price,
                                    'currency_id': currency.id,
                                    'delay': 0,
                                }
                                # In case the order partner is a contact address, a new supplierinfo is created on
                                # the parent company. In this case, we keep the product name and code.
                                seller = line.product_id._select_seller(
                                    partner_id=line.partner_id,
                                    quantity=line.product_qty,
                                    date=line.order_id.date_order and line.order_id.date_order.date(),
                                    uom_id=line.product_uom)
                                if seller:
                                    supplierinfo['product_name'] = seller.product_name
                                    supplierinfo['product_code'] = seller.product_code
                                vals = {
                                    'seller_ids': [(0, 0, supplierinfo)],
                                }
                                line.product_id.write(vals)
            except AccessError:  # no write access rights -> just ignore
                break