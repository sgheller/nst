# -*- coding: utf-8 -*-
from odoo import fields, models, api
from itertools import groupby


class EmpName(models.Model):
    _inherit = "sale.order.line"

    order_line_delivery_date = fields.Date(string='Delivery Date')


class StockMove(models.Model):
    _inherit = "stock.move"

    def _assign_picking(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        Picking = self.env['stock.picking']
        grouped_moves = groupby(sorted(self, key=lambda m: [f.id for f in m._key_assign_picking()]),
                                key=lambda m: [m._key_assign_picking()])
        for group, moves in grouped_moves:

            moves = self.env['stock.move'].concat(*list(moves))
            new_picking = False
            for move in moves:
                # Could pass the arguments contained in group but they are the same
                # for each move that why moves[0] is acceptable
                picking = move._search_picking_for_assignation()
                if picking:
                    if any(picking.partner_id.id != m.partner_id.id or
                           picking.origin != m.origin for m in moves):
                        # If a picking is found, we'll append `move` to its move list and thus its
                        # `partner_id` and `ref` field will refer to multiple records. In this
                        # case, we chose to  wipe them.
                        picking.write({
                            'partner_id': False,
                            'origin': False,
                        })
                else:
                    new_picking = True
                    picking = Picking.create(move._get_new_picking_values())

                move.write({'picking_id': picking.id})
                move._assign_picking_post_process(new=new_picking)
        return True

    def _search_picking_for_assignation(self):
        self.ensure_one()
        picking = self.env['stock.picking'].search([
                ('group_id', '=', self.group_id.id),
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_dest_id.id),
                ('picking_type_id', '=', self.picking_type_id.id),
                ('order_line_delivery_date', '=', self.sale_line_id.order_line_delivery_date),
                ('printed', '=', False),
                ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
        return picking

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        if self.sale_line_id.order_line_delivery_date:
            res['order_line_delivery_date'] = self.sale_line_id.order_line_delivery_date
        return res


class StockPicking(models.Model):
    _inherit = "stock.picking"

    order_line_delivery_date = fields.Date(string='Delivery Date')

