# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    # shipping_weight = fields.Float(string='Shipping Weight', help="Total weight of the package.", compute="_compute_shipping_weight", store=True)
    #
    # @api.depends('quant_ids')
    # def _compute_shipping_weight(self):
    #     for package in self:
    #         weight = 0.0
    #         if self.env.context.get('picking_id'):
    #             # TODO: potential bottleneck: N packages = N queries, use groupby ?
    #             current_picking_move_line_ids = self.env['stock.move.line'].search([
    #                 ('result_package_id', '=', package.id),
    #                 ('picking_id', '=', self.env.context['picking_id'])
    #             ])
    #             for ml in current_picking_move_line_ids:
    #                 weight += ml.product_uom_id._compute_quantity(
    #                     ml.qty_done, ml.product_id.uom_id) * ml.product_id.weight
    #         else:
    #             for quant in package.quant_ids:
    #                 weight += quant.quantity * quant.product_id.weight
    #         package.shipping_weight = weight
