# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    cash_flow = fields.One2many('phi_cash_flow.cash.flow', 'account_analytic_line_id', string='Cash Flow', copy=False)

    def write(self, values):
        result = super(AccountAnalyticLine, self).write(values)
        if len(self) and (values.get("analytic_account_id") or values.get("date_planned") or values.get("state") or values.get("payment_term_id")):
            self.create_cash_flow_entries()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(AccountAnalyticLine, self).create(vals_list)
        for line in lines:
            line.create_cash_flow_entries()
        return lines

    def create_cash_flow_entries(self):
        self.ensure_one()

        self.cash_flow.unlink()

        if not self.account_id:
            return

        if self.move_id and self.move_id.move_id.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
            return

        casflow_object = self.env["phi_cash_flow.cash.flow"]
        if self.env.company.currency_id != self.currency_id:
            amount = self.currency_id._convert(self.amount, self.env.company.currency_id, self.env.company, self.date)
        else:
            amount = self.amount
        casflow_object.create({
            'account_analytic_line_id': self.id,
            'account_analytic_id': self.account_id.id,
            'date': self.date,
            'move_type': 'real',
            'amount_in': amount if amount > 0 else 0.0,
            'amount_out': amount if amount < 0 else 0.0,
        })
