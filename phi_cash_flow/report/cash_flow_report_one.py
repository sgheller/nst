# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import api, fields, models, _
from odoo.addons.web.controllers.main import clean_action
from odoo.tools import date_utils


class AnalyticCashflowReportOne(models.AbstractModel):
    _inherit = 'phi_cash_flow.analytic.cashflow.report'
    _name = 'phi_cash_flow.analytic.cashflow.report.one'
    _description = 'Cash Flow Report'

    # filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_date = None
    filter_analytic = False
    filter_hierarchy = False
    filter_unfold_all = None

    def _get_analytic_accounts_ids(self):
        if self._context.get('active_model') == 'account.analytic.account':
            return self._context.get('active_ids')
        elif self._context.get('active_model') == 'sale.order':
            sale = self.env["sale.order"].browse(self._context.get('active_id'))
            if sale.analytic_account_id:
                return sale.analytic_account_id.ids
        return False

    @api.model
    def _get_options(self, previous_options=None):
        options = super(AnalyticCashflowReportOne, self)._get_options(previous_options)
        options['analytic_accounts'] = self._get_analytic_accounts_ids()
        options['analytic'] = False
        return options