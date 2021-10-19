# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        for order in self:
            if order.partner_id:
                order.incoterm = order.partner_id.so_incoterm_id if order.partner_id.so_incoterm_id else order.partner_id.parent_id.so_incoterm_id

    @api.model
    def create(self, vals):
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        if partner.so_incoterm_id and not vals.get('incoterm'):
            vals['incoterm'] = partner.so_incoterm_id.id
        result = super(SaleOrder, self).create(vals)
        return result