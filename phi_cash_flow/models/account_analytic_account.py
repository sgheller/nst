# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    cash_flow_forecast = fields.One2many('phi_cash_flow.cash.flow', 'account_analytic_id', string='Cash Flow', copy=False, domain=[('move_type', '=', 'forecast')], tracking=True)
    cash_flow_forecast_balance = fields.Monetary(string="Cash Flow Forecast Balance", compute="_compute_cash_flow_forecast_balance", tracking=True, store=True)

    @api.depends('cash_flow_forecast.amount_in','cash_flow_forecast.amount_out')
    def _compute_cash_flow_forecast_balance(self):
        for account in self:
            account.cash_flow_forecast_balance = sum(account.cash_flow_forecast.mapped('balance'))
