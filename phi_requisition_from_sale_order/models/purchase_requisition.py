# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    sale_id = fields.Many2one('sale.order', 'Sale Order')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Compte Analytique')

    def purchase_requisition_add_products(self):
        compose_form = self.env.ref('phi_requisition_from_sale_order.view_purchase_requisition_add_products', raise_if_not_found=False)

        return {
            'name': _('Add Products'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.requisition.add.products',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
        }

    def generate_default_purchase_orders(self):
        self.ensure_one()
        if not self.vendor_id:
            for line in self.line_ids:
                vendors = line.product_id.seller_ids.mapped('name')
                for vendor in vendors:
                    purchase_order = self.purchase_ids.filtered(lambda s: s.partner_id == vendor)
                    if not purchase_order:
                        purchase_order = self.env['purchase.order'].create({
                            'partner_id': vendor.id,
                            'requisition_id': self.id,
                            'date_order': self.ordering_date or self.write_date,
                            'account_analytic_id': self.account_analytic_id.id,
                        })
                    self.env['purchase.order.line'].create({
                        'order_id': purchase_order.id,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom_id.id,
                        'date_planned': line.schedule_date or self.schedule_date or purchase_order.date_order,
                    })
        else:
            vendor = self.vendor_id
            purchase_order = self.purchase_ids.filtered(lambda s: s.partner_id == vendor)
            if not purchase_order:
                purchase_order = self.env['purchase.order'].create({
                    'partner_id': vendor.id,
                    'requisition_id': self.id,
                    'date_order': self.ordering_date or self.write_date,
                    'account_analytic_id': self.account_analytic_id.id,
                })
            for line in self.line_ids:
                self.env['purchase.order.line'].create({
                    'order_id': purchase_order.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom': line.product_uom_id.id,
                    'date_planned': line.schedule_date or self.schedule_date or purchase_order.date_order,
                })