# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools import date_utils, DEFAULT_SERVER_DATE_FORMAT


class AccountMove(models.Model):
    _inherit = 'account.move'

    cash_flow = fields.One2many('phi_cash_flow.cash.flow', 'invoice_id', string='Cash Flow', copy=False)

    def write(self, values):
        result = super(AccountMove, self).write(values)
        if values.get("analytic_account_id") or values.get("invoice_date") or values.get("state") or values.get("invoice_payment_term_id"):
            self.create_cash_flow_entries()
        return result

    def create_cash_flow_entries(self):
        self.ensure_one()
        # delete old entries
        self.cash_flow.unlink()

        if self.state == 'posted' and self.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
            is_sale = self.move_type in ('out_invoice', 'out_refund')
            analytic_accounts = self.invoice_line_ids.mapped('analytic_account_id')
            for account in analytic_accounts:
                entries = []
                for line in self.invoice_line_ids.filtered(lambda line: line.analytic_account_id == account):
                    date = self.invoice_date or fields.Datetime.now().date()
                    if self.invoice_payment_term_id:
                        payment_terms = self.invoice_payment_term_id.compute(line.price_total, date)
                    else:
                        payment_terms = [(fields.Date.to_string(date), line.price_total)]
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
                        amount = self.currency_id._convert(entry["amount"], self.env.company.currency_id, self.env.company, self.invoice_date)
                    else:
                        amount = entry["amount"]
                    casflow_object.create({
                        'invoice_id': self.id ,
                        'account_analytic_id': account.id,
                        'date': entry["date"],
                        'move_type': 'real',
                        'amount_in': amount if is_sale else 0,
                        'amount_out': amount if not is_sale else 0,
                    })

        for order in self.invoice_line_ids.sale_line_ids.mapped('order_id'):
            order.create_cash_flow_entries()
        for order in self.invoice_line_ids.purchase_line_id.mapped('order_id'):
            order.create_cash_flow_entries()
        for order in self.invoice_line_ids.mapped('purchase_order_id'):
            order.create_cash_flow_entries()

