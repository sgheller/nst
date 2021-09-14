# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import date_utils
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


class CashFlow(models.Model):
    _name = 'phi_cash_flow.cash.flow'
    _description = 'Cash Flow'
    _order = "date"

    account_analytic_id = fields.Many2one('account.analytic.account', string='Compte Analytique', store=True, index=True)
    name = fields.Char(string='Number', copy=False, compute='_compute_name', readonly=False, store=True, index=True, tracking=True)
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        copy=False,
    )
    move_type = fields.Selection(selection=[
            ('forecast', 'Forecast'),
            ('real', 'Réalisé'),
        ], string='Type', required=True, store=True, index=True, readonly=True, tracking=True,
        default="forecast", change_default=True)
    amount_in = fields.Monetary(string='Amount In', tracking=True)
    amount_out = fields.Monetary(string='Amount Out', tracking=True)
    balance = fields.Monetary(string='Balance', tracking=True, compute='_compute_balance')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)
    date_end_month = fields.Date(string='Date end Month', compute="_compute_date_end_month", index=True)
    sale_id = fields.Many2one('sale.order', 'Sale Order', index=True)
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order', index=True)
    balance_real_previsionnal = fields.Monetary(string='Balance', compute='_compute_balance_real_previsionnal')
    invoice_id = fields.Many2one('account.move', 'Invoice', index=True)

    @api.depends('account_analytic_id', 'move_type', 'date')
    def _compute_name(self):
        for move in self:
            if move.move_type == 'forecast':
                move.name = _('forecast')
            elif move.move_type == 'real':
                if move.sale_id:
                    move.name = move.sale_id.name
                elif move.purchase_id:
                    move.name = move.purchase_id.name
                elif move.invoice_id:
                    move.name = move.invoice_id.name
            else:
                move.name = ''


    @api.depends('amount_in', 'amount_out')
    def _compute_balance(self):
        for move in self:
            move.balance = move.amount_in - move.amount_out

    @api.depends('amount_in', 'amount_out')
    def _compute_balance_real_previsionnal(self):
        for move in self:
            if move.move_type == 'forecast':
                move.balance_real_previsionnal = move.balance * -1
            else:
                move.balance_real_previsionnal = move.balance

    def _valid_field_parameter(self, field, name):
        # I can't even
        return name == 'tracking' or super()._valid_field_parameter(field, name)

    @api.depends('date')
    def _compute_date_end_month(self):
        for move in self:
            if move.date < fields.Datetime.now().date() and ( move.sale_id or move.purchase_id or move.invoice_id):
                date = fields.Datetime.now().date() + relativedelta(months=1)
            else:
                date = move.date
            move.date_end_month = date_utils.end_of(date, "month")
