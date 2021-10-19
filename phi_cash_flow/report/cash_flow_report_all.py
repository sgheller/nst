# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import api, fields, models, _
from odoo.addons.web.controllers.main import clean_action
from odoo.tools import date_utils


class AnalyticCashflowReportAll(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'phi_cash_flow.analytic.cashflow.report.all'
    _description = 'Cash Flow Report'

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_analytic = True
    filter_hierarchy = False
    filter_unfold_all = None

    def _get_columns_name(self, options):
        columns = [{'name': ''},
                   {'name': 'Compte Analytique'},
                   {'name': 'Prévisionnel recette', 'class': 'number'},
                   {'name': 'Prévisionnel dépenses', 'class': 'number'},
                   {'name': 'Ecart prévisionnel', 'class': 'number'},
                   {'name': 'Recettes', 'class': 'number'},
                   {'name': 'Dépenses', 'class': 'number'},
                   {'name': 'Ecart sur le réalisé', 'class': 'number'},
                   ]

        return columns

    @api.model
    def _get_report_name(self):
        return _('Analytic Report Cash Flow')

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        analytic_entries_domain = self._generate_domain(options)
        analytic_entries = self.env['phi_cash_flow.cash.flow'].search(analytic_entries_domain)

        analytic_accounts = analytic_entries.mapped('account_analytic_id').sorted('name')

        total_forecast_in = 0.0
        total_forecast_out = 0.0
        total_real_in = 0.0
        total_real_out = 0.0
        for account in analytic_accounts:
            forecast = analytic_entries.filtered(lambda line: line.account_analytic_id.id == account.id and line.move_type == 'forecast')
            forecast_in = sum(forecast.mapped('amount_in'))
            forecast_out = sum(forecast.mapped('amount_out'))

            real = analytic_entries.filtered(lambda line: line.account_analytic_id.id == account.id and line.move_type == 'real')
            real_in = sum(real.mapped('amount_in'))
            real_out = sum(real.mapped('amount_out'))
            columns = [{'name': account.name},
                       {'name': round(forecast_in, 2) if forecast_in else ''},
                       {'name': round(forecast_out, 2) if forecast_out else ''},
                       {'name': round(forecast_in - forecast_out , 2) if forecast_in - forecast_out else '', 'class': "number color-red" if forecast_in - forecast_out < 0 else "number"},
                       {'name': round(real_in, 2) if real_in else ''},
                       {'name': round(real_out, 2) if real_out else ''},
                       {'name': round(real_in - real_out , 2) if real_in - real_out else '', 'class': "number color-red" if real_in - real_out < 0 else "number"},
                       ]

            lines.append({
                    'id': 'account_%s' % account.id,
                    'columns': columns,
                    'unfoldable': False,
                    'unfolded': False,
                })

            total_forecast_in += forecast_in
            total_forecast_out += forecast_out
            total_real_in += real_in
            total_real_out += real_out

        if len(analytic_accounts):
            columns = [{'name': 'Total', 'class': "o_account_reports_level1"},
                       {'name': round(total_forecast_in, 2) if total_forecast_in else '', 'class': "number o_account_reports_level1"},
                       {'name': round(total_forecast_out, 2) if total_forecast_out else '', 'class': "number o_account_reports_level1"},
                       {'name': round(total_forecast_in - total_forecast_out, 2), 'class': "number o_account_reports_level1 color-red" if total_forecast_in - total_forecast_out < 0 else "number o_account_reports_level1"},
                       {'name': round(total_real_in, 2) if total_real_in else '', 'class': "number o_account_reports_level1"},
                       {'name': round(total_real_out, 2) if total_real_out else '', 'class': "number o_account_reports_level1"},
                       {'name': round(total_real_in - total_real_out, 2), 'class': "number o_account_reports_level1 color-red" if total_real_in - total_real_out < 0 else "number o_account_reports_level1"},
                       ]

            lines.append({
                'id': 'account_%s' % account.id,
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        return lines

    def _generate_domain(self, options):
        analytic_entries_domain = []
        if options.get('date'):
            date_from = options['date']['date_from']
            date_to = options['date']['date_to']
            analytic_entries_domain += [('date', '>=', date_from), ('date', '<=', date_to)]

        if options['analytic_accounts']:
            analytic_account_ids = [int(id) for id in options['analytic_accounts']]
            analytic_entries_domain += [('account_analytic_id', 'in', analytic_account_ids)]
        if options.get('multi_company'):
            company_ids = self.env.companies.ids
        else:
            company_ids = self.env.company.ids
        analytic_entries_domain += ['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]
        return analytic_entries_domain

