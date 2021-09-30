# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_ticket_ids = fields.One2many('helpdesk.ticket', 'purchase_order_id', string='Tickets Achat')
    purchase_ticket_count = fields.Integer(string='Tickets', compute='_compute_purchase_ticket_ids')

    @api.depends('purchase_ticket_ids')
    def _compute_purchase_ticket_ids(self):
        for order in self:
            order.purchase_ticket_count = len(order.purchase_ticket_ids)

    def action_open_purchase_helpdesk_ticket(self):
        action = self.env.ref('helpdesk.helpdesk_ticket_action_main_tree').read()[0]
        action['context'] = {}
        action['domain'] = [('purchase_order_id', '=', self.id)]
        return action
