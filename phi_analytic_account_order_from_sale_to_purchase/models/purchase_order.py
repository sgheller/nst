# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def write(self, values):
        if not self.account_analytic_id and values.get('analytic_account_id') == None:
            analytic_account_id = self._get_sale_analytic_account()
            if analytic_account_id:
                values["account_analytic_id"] = analytic_account_id
        return super(PurchaseOrderLine, self).write(values)

    def _get_sale_order(self):
        return self.sale_order_id | self.move_dest_ids.group_id.sale_id | self.move_ids.move_dest_ids.group_id.sale_id

    def _get_sale_analytic_account(self):
        sale_orders = self._get_sale_order()
        for order in sale_orders:
            if order.analytic_account_id:
                return order.analytic_account_id.id
        return False

    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        if values.get('group_id') and values['group_id'].sale_id and values['group_id'].sale_id.analytic_account_id:
            analytic_account_id = values['group_id'].sale_id.analytic_account_id
        else:
            analytic_account_id = False
        if analytic_account_id:
            lines = self.filtered(lambda po_line: po_line.account_analytic_id == analytic_account_id)
        else:
            lines = self.filtered(lambda po_line: not po_line.account_analytic_id )
        return super(PurchaseOrderLine, lines)._find_candidate(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
