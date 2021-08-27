# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleRequisitionGenerate(models.TransientModel):
    _name = 'purchase_requisition.requisition.generate'
    _description = 'Generate Requisition From Sale Order'

    lines_ids = fields.Many2many('sale.order.line')

    @api.model
    def default_get(self, fields):
        res = super(SaleRequisitionGenerate, self).default_get(fields)
        res_ids = self._context.get('active_ids')

        sale_order = self.env["sale.order"].browse(res_ids)
        lines_ids = sale_order.order_line.filtered(lambda s: s.product_id and s.product_id.purchase_ok and s.product_id.seller_ids)
        res['lines_ids'] = [(6, 0, lines_ids.ids)]

        return res

    def generate(self):
        res_ids = self._context.get('active_ids')
        sale_order = self.env["sale.order"].browse(res_ids)
        for record in self:
            # create requisition
            if len(record.lines_ids):
                purchase_vals = {
                    'type_id': self.env.ref('purchase_requisition.type_multi').id,
                    'company_id': self.env.company.id,
                    'currency_id': self.env.company.currency_id.id,
                    'origin': sale_order.name,
                    'sale_id': sale_order.id,
                }
                requisition = self.env["purchase.requisition"].create(purchase_vals)
            for line in record.lines_ids:
                line_vals = {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_uom_qty,
                    'product_uom_id': line.product_uom.id,
                    'requisition_id': requisition.id,
                }
                self.env["purchase.requisition.line"].create(line_vals)
            requisition.action_in_progress()
            requisition.generate_default_purchase_orders()






