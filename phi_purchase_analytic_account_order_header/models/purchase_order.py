# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    account_analytic_id = fields.Many2one('account.analytic.account', string='Compte Analytique', store=True)

    @api.onchange('account_analytic_id')
    def _onchange_account_analytic_id(self):
        for order in self:
            for line in order.order_line:
                line.account_analytic_id = order.account_analytic_id


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.account_analytic_id = self.order_id.account_analytic_id

    @api.model
    def create(self, vals):
        if not vals.get('account_analytic_id'):
            if vals.get('order_id'):
                vals['account_analytic_id'] = self.env['purchase.order'].browse(vals.get('order_id')).account_analytic_id.id

        if not vals.get('account_analytic_id'):
            if vals.get('partner_id'):
                vals['account_analytic_id'] = self.env['res.partner'].browse(vals.get('partner_id')).get_account_analytic().id

        return super(PurchaseOrderLine, self).create(vals)