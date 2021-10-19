# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import api, fields, models, _
from odoo.addons.web.controllers.main import clean_action
from odoo.tools import date_utils


class AnalyticCashflowReport(models.AbstractModel):
    _inherit = 'phi_cash_flow.analytic.cashflow.report'


    @api.model
    def _get_options(self, previous_options=None):
        options = super(AnalyticCashflowReport, self)._get_options(previous_options)
        if self._context.get('active_model') == 'crm.lead':
            lead = self.env["crm.lead"].browse(self._context.get('active_id'))
            if lead.account_analytic_id:
                options['analytic_accounts'] = lead.account_analytic_id.ids
                options['analytic'] = False
        return options
