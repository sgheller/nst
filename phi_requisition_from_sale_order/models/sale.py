# -*- coding: utf-8 -*-

from odoo import models, fields, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    requisition_ids = fields.One2many('purchase.requisition', 'sale_id', string='Purchase Agreement')
    requisitions_count = fields.Integer(string='Requisition count', compute='_compute_requisition_count')

    def action_view_requisitions(self):
        self.ensure_one()
        action = {
            'res_model': 'purchase.requisition',
            'type': 'ir.actions.act_window',
        }
        if self.requisitions_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.requisition_ids.ids[0],
            })
        else:
            action.update({
                'name': _("Requisition from sale order %s", self.name),
                'domain': [('id', 'in', self.requisition_ids.ids)],
                'view_mode': 'tree,form',
            })
        return action

    def requisition_count(self):
        return len(self.requisition_ids.filtered(lambda s: s.state != 'cancel'))

    def _compute_requisition_count(self):
        for order in self:
            order.requisitions_count = order.requisition_count()

    def action_requisition(self):
        action = self.env.ref('phi_requisition_from_sale_order.action_sale_requisition_generate').read()[0]

        compose_form = self.env.ref('phi_requisition_from_sale_order.view_sale_requisition_generate', raise_if_not_found=False)

        return {
            'name': _('Generate Sale Requisition'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase_requisition.requisition.generate',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    purchase_last_date = fields.Date(related="product_id.purchase_last_date")
    purchase_last_partner_id = fields.Many2one(related="product_id.purchase_last_partner_id")
    current_requisition = fields.Char(related="product_id.current_requisition")