# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    incoterm_description = fields.Text("Incoterm Description")
    incoterm_is_additionnal_info = fields.Boolean(related="incoterm.is_additionnal_info")
    incoterm_full_name = fields.Char(compute="_compute_incoterm_full_name")

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.incoterm_description:
            res['incoterm_description'] = self.incoterm_description
        return res

    def _compute_incoterm_full_name(self):
        for order in self:
            if not order.incoterm:
                order.incoterm_full_name = False
            else:
                order.incoterm_full_name = "\n".join([order.incoterm.code, order.incoterm_description])

    @api.onchange('incoterm', 'partner_id', 'partner_shipping_id', 'warehouse_id')
    def get_incoterm_description(self):
        for order in self:
            if not order.incoterm:
                order.incoterm_description = False
            else:
                order.incoterm_description = order.incoterm.get_additionnal_informations(order.warehouse_id.partner_id, order.partner_shipping_id)