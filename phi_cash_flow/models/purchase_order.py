# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools import date_utils, DEFAULT_SERVER_DATE_FORMAT

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    cash_flow = fields.One2many('phi_cash_flow.cash.flow', 'purchase_id', string='Cash Flow', copy=False)

    def write(self, values):
        result = super(PurchaseOrder, self).write(values)
        if len(self) and (values.get("analytic_account_id") or values.get("date_planned") or values.get("state") or values.get("payment_term_id")):
            self.create_cash_flow_entries()
        return result

    def create_cash_flow_entries(self):
        self.ensure_one()
        # delete old entries
        self.cash_flow.unlink()

        if self.state in ('purchase', 'done'):
            analytic_accounts = self.order_line.mapped('account_analytic_id')
            for account in analytic_accounts:
                entries = []
                for line in self.order_line.filtered(lambda line: line.account_analytic_id == account):
                    date = line.date_planned or self.date_planned or fields.Datetime.now().date()
                    if self.payment_term_id:
                        payment_terms = self.payment_term_id.compute(line.amount_not_invoices_gross, date)
                    else:
                        payment_terms = [(fields.Date.to_string(date), line.amount_not_invoices_gross)]
                    for term in payment_terms:
                        term_date = fields.datetime.strptime(term[0], DEFAULT_SERVER_DATE_FORMAT).date()
                        entry_date = [i for i in entries if i['date'] == term_date]
                        if not entry_date:
                            entries.append({'date': term_date, 'amount': term[1]})
                        else:
                            entry_date[0]["amount"] += term[1]

                casflow_object = self.env["phi_cash_flow.cash.flow"]
                for entry in entries:
                    if self.env.company.currency_id != self.currency_id:
                        amount = self.currency_id._convert(entry["amount"], self.env.company.currency_id, self.env.company, self.date_planned)
                    else:
                        amount = entry["amount"]
                    casflow_object.create({
                        'purchase_id': self.id,
                        'account_analytic_id': account.id,
                        'date': entry["date"],
                        'move_type': 'real',
                        'amount_in': 0.0,
                        'amount_out': amount,
                    })


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    amount_not_invoices_gross = fields.Monetary(compute='_compute_amount_not_invoices_gross', string='Total gross not invoiced', readonly=True, store=True)

    def write(self, values):
        result = super(PurchaseOrderLine, self).write(values)
        if values.get("product_uom_qty") or values.get("qty_invoiced") or values.get("price_total") or values.get("date_planned") or values.get("account_analytic_id"):
            self.order_id.create_cash_flow_entries()
        return result

    @api.depends('price_total', 'qty_invoiced', 'product_uom_qty')
    def _compute_amount_not_invoices_gross(self):
        for line in self:
            if line.product_uom_qty and line.product_id:
                line.amount_not_invoices_gross = (line.price_total / line.product_uom_qty) * (line.product_uom_qty - line.qty_invoiced)
            else:
                line.amount_not_invoices_gross = 0

