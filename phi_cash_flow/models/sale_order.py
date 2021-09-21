# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools import date_utils, DEFAULT_SERVER_DATE_FORMAT

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cash_flow = fields.One2many('phi_cash_flow.cash.flow', 'sale_id', string='Cash Flow', copy=False)

    def _action_confirm(self):
        for order in self:
            order.create_cash_flow_entries()
        return super(SaleOrder, self)._action_confirm()

    def write(self, values):
        result = super(SaleOrder, self).write(values)
        if values.get("analytic_account_id") or values.get("commitment_date") or values.get("state") or values.get("payment_term_id"):
            for order in self:
                order.create_cash_flow_entries()
        return result

    def create_cash_flow_entries(self):
        self.ensure_one()
        # delete old entries
        self.cash_flow.unlink()

        if self.state in ('sale', 'done') and self.amount_untaxed:
            entries = []

            # récuparation des acomptes
            advance_proportion = 1
            advance = sum(self.order_line.filtered(lambda x: x.is_downpayment).mapped('price_unit'))
            if advance:
                advance_proportion = 1 - (advance / self.amount_untaxed)

            for line in self.order_line:
                date = line.order_line_delivery_date or self.commitment_date or fields.Datetime.now().date()
                if self.payment_term_id:
                    payment_terms = self.payment_term_id.compute(line.amount_not_invoices_gross, date)
                else:
                    payment_terms = [(fields.Date.to_string(date), line.amount_not_invoices_gross)]
                for term in payment_terms:
                    term_date = fields.datetime.strptime(term[0], DEFAULT_SERVER_DATE_FORMAT).date()
                    entry_date = [i for i in entries if i['date'] == term_date]
                    if not entry_date:
                        entries.append({'date': term_date, 'amount': term[1] * advance_proportion})
                    else:
                        entry_date[0]["amount"] += term[1] * advance_proportion

            casflow_object = self.env["phi_cash_flow.cash.flow"]
            for entry in entries:
                if self.env.company.currency_id != self.currency_id:
                    amount = self.currency_id._convert(entry["amount"], self.env.company.currency_id, self.env.company, self.date_order)
                else:
                    amount = entry["amount"]
                casflow_object.create({
                    'sale_id': self.id,
                    'account_analytic_id': self.analytic_account_id.id,
                    'date': entry["date"],
                    'move_type': 'real',
                    'amount_in': amount,
                    'amount_out': 0.0,
                })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    amount_not_invoices_gross = fields.Monetary(compute='_compute_amount_not_invoices_gross', string='Total gross not invoiced', readonly=True, store=True)

    def write(self, values):
        result = super(SaleOrderLine, self).write(values)
        if values.get("product_uom_qty") or values.get("price_total") or values.get("qty_invoiced") or values.get("order_line_delivery_date"):
            self.order_id.create_cash_flow_entries()
        return result

    @api.depends('price_total', 'qty_invoiced', 'product_uom_qty')
    def _compute_amount_not_invoices_gross(self):
        for line in self:
            if line.product_uom_qty and line.product_id:
                line.amount_not_invoices_gross = (line.price_total / line.product_uom_qty) * (line.product_uom_qty - line.qty_invoiced)
            else:
                line.amount_not_invoices_gross = 0

