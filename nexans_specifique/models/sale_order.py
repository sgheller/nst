# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    purchase_price_index = fields.Many2one('phi_purchase_price_index.purchase.index', string='Indice Prix', compute="_computepurchase_price_index")
    indice_meps = fields.Date("Indice Meps")
    customer_text = fields.Text(strin="Texte Client")

    @api.onchange('opportunity_id')
    def onchange_opportunity_id(self):
        for order in self:
            if order.opportunity_id:
                order.analytic_account_id = order.opportunity_id.account_analytic_id

    @api.model
    def create(self, vals):
        if vals.get('opportunity_id') and not vals.get('analytic_account_id'):
            lead = self.env['crm.lead'].browse(vals.get('opportunity_id'))
            if lead.account_analytic_id:
                vals['analytic_account_id'] = lead.account_analytic_id.id
        result = super(SaleOrder, self).create(vals)
        return result

    def _computepurchase_price_index(self):
        for order in self:
            order.purchase_price_index = self.env["phi_purchase_price_index.purchase.index"]._get_current_index(order.date_order)