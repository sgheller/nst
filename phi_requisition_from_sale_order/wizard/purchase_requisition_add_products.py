# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseRequisitionAddProducts(models.TransientModel):
    _name = 'purchase.requisition.add.products'
    _description = 'Requisition add products'

    product_ids = fields.Many2many('product.product')

    # @api.model
    # def default_get(self, fields):
    #     res = super(PurchaseRequisitionAddProducts, self).default_get(fields)
    #     res_ids = self._context.get('active_ids')
    #
    #     invoice = self.env["account.move"].browse(res_ids)
    #
    #     return res

    def select_lines(self):
        for record in self:
            new_lines = self.env['purchase.requisition.line']
            res_ids = self._context.get('active_ids')
            requisition = self.env["purchase.requisition"].browse(res_ids)
            for product in record.product_ids:
                line_vals = {
                    'product_id': product.id,
                    'product_qty': 1,
                    'product_uom_id': product.uom_po_id.id,
                    'requisition_id': requisition.id,
                }
                new_line = new_lines.new(line_vals)
                new_lines += new_line
                requisition.line_ids += new_line
