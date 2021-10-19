# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(PurchaseOrder, self).onchange_partner_id()
        for order in self:
            if order.partner_id:
                order.incoterm_id = order.partner_id.incoterm_id if order.partner_id.incoterm_id else order.partner_id.parent_id.incoterm_id
