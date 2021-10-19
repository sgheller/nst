# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if any([ptype in ['product', 'consu'] for ptype in order.order_line.mapped('product_id.type')]):
                dates_picking = []
                for line in order.order_line.filtered(lambda l: not l.display_type):
                    if line.date_planned.date() not in dates_picking:
                        dates_picking.append(line.date_planned.date())

                for date_picking in dates_picking:
                    pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.date.date() == date_picking)
                    if not pickings:
                        self.group_id = self.group_id.create({
                            'name': self.name,
                            'partner_id': self.partner_id.id,
                        })
                        res = order._prepare_picking()
                        res["date"] = date_picking
                        res["order_line_delivery_date"] = date_picking
                        picking = StockPicking.create(res)
                    else:
                        picking = pickings[0]
                    moves = order.order_line._create_stock_moves(picking)
                    moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                    seq = 0
                    for move in sorted(moves, key=lambda move: move.date):
                        seq += 5
                        move.sequence = seq
                    moves._action_assign()
                    picking.message_post_with_view('mail.message_origin_link',
                        values={'self': picking, 'origin': order},
                        subtype_id=self.env.ref('mail.mt_note').id)
        return True


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _create_stock_moves(self, picking):
        values = []
        for line in self.filtered(lambda l: not l.display_type and l.date_planned.date() == picking.date.date()):
            for val in line._prepare_stock_moves(picking):
                values.append(val)
        return self.env['stock.move'].create(values)