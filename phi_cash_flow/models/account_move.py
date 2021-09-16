# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools import date_utils, DEFAULT_SERVER_DATE_FORMAT


class AccountMove(models.Model):
    _inherit = 'account.move'

    cash_flow = fields.One2many('phi_cash_flow.cash.flow', 'invoice_id', string='Cash Flow', copy=False)

    def button_draft(self):
        res = super().button_draft()
        for move in self:
            if move.cash_flow:
                move.cash_flow.unlink()
        return res

    def create_cash_flow_entries(self):
        for move in self:
            move.ensure_one()
            # delete old entries
            move.cash_flow.unlink()

            if not move.amount_total:
                continue

            if move.state == 'posted' and move.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                is_sale = move.move_type in ('out_invoice', 'in_refund')
                casflow_object = self.env["phi_cash_flow.cash.flow"]
                analytic_accounts = move.invoice_line_ids.mapped('analytic_account_id')

                account_proportion = []
                for account in analytic_accounts:
                    amount = sum(move.invoice_line_ids.filtered(lambda line: line.analytic_account_id == account).mapped('price_total'))
                    account_proportion.append({'account': account.id, 'proportion': amount/move.amount_total})

                reconciled_payments = move._get_reconciled_payments()
                for payment in reconciled_payments:
                    for account in analytic_accounts:
                        proportion = self._get_account_move_propostion(account, account_proportion)
                        if proportion:
                            amount = payment.amount * proportion
                            if self.env.company.currency_id != payment.currency_id:
                                amount = payment.currency_id._convert(amount, self.env.company.currency_id, self.env.company, payment.date)
                            else:
                                amount = amount

                            casflow_object.create({
                                'invoice_id': move.id,
                                'account_analytic_id': account.id,
                                'date': payment.date,
                                'move_type': 'real',
                                'amount_in': amount if is_sale else 0,
                                'amount_out': amount if not is_sale else 0,
                                'is_fixed_date': True,
                            })

                for account in analytic_accounts:
                    entries = []
                    for line in move.invoice_line_ids.filtered(lambda line: line.analytic_account_id == account):
                        date = move.invoice_date or fields.Datetime.now().date()
                        if move.invoice_payment_term_id:
                            payment_terms = move.invoice_payment_term_id.compute(line.price_total, date)
                        else:
                            payment_terms = [(fields.Date.to_string(date), line.price_total)]
                        for term in payment_terms:
                            term_date = fields.datetime.strptime(term[0], DEFAULT_SERVER_DATE_FORMAT).date()
                            entry_date = [i for i in entries if i['date'] == term_date]
                            if not entry_date:
                                entries.append({'date': term_date, 'amount': term[1]})
                            else:
                                entry_date[0]["amount"] += term[1]

                    proportion = self._get_account_move_propostion(account, account_proportion)
                    amount_paid = (move.amount_total - move.amount_residual) * proportion
                    for entry in entries:
                        if move.env.company.currency_id != move.currency_id:
                            amount = move.currency_id._convert(entry["amount"], move.env.company.currency_id, move.env.company, move.invoice_date)
                        else:
                            amount = entry["amount"]
                        amount = amount
                        if abs(amount_paid) >= abs(amount):
                            amount_paid = amount_paid - amount
                        else:
                            amount = amount - amount_paid
                            casflow_object.create({
                                'invoice_id': move.id ,
                                'account_analytic_id': account.id,
                                'date': entry["date"],
                                'move_type': 'real',
                                'amount_in': amount if is_sale else 0,
                                'amount_out': amount if not is_sale else 0,
                            })

            for order in move.invoice_line_ids.sale_line_ids.mapped('order_id'):
                order.create_cash_flow_entries()
            for order in move.invoice_line_ids.purchase_line_id.mapped('order_id'):
                order.create_cash_flow_entries()
            for order in move.invoice_line_ids.mapped('purchase_order_id'):
                order.create_cash_flow_entries()

    def _get_account_move_propostion(self, account, account_proportion):
        proportion_list = [d for d in account_proportion if d['account'] == account.id]
        if len(proportion_list):
            proportion = proportion_list[0]['proportion']
        else:
            proportion = 0
        return proportion

    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for move in self:
            if move.state == 'posted' and move.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                move.create_cash_flow_entries()
