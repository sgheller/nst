# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_category_id = fields.Many2one('phi_purchase_category.purchase_category', string='Purchase Category')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(PurchaseOrder, self).onchange_partner_id()
        for order in self:
            if order.partner_id:
                order.purchase_category_id = order.partner_id.purchase_category_id if order.partner_id.purchase_category_id else order.partner_id.parent_id.purchase_category_id

    @api.model
    def create(self, vals):
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        if partner.purchase_category_id and not vals.get('purchase_category_id'):
            vals['purchase_category_id'] = partner.purchase_category_id.id
        result = super(PurchaseOrder, self).create(vals)
        return result