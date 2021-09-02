# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    current_requisition = fields.Char("Active Requisition", compute="_compute_current_requisition")

    def _compute_current_requisition(self):
        for product in self:
            lines = self.env["purchase.requisition.line"].search([
                ('product_id', '=', product.id if isinstance(product.id, int) else product.id.origin),
                ('requisition_id.state', 'not in', ('cancel', 'done'))
            ])
            if len(lines):
                requisitions = set(lines.requisition_id.mapped('name'))
                product.current_requisition = ','.join(list(requisitions))
            else:
                product.current_requisition = False
