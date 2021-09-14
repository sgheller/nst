# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import api, fields, models, _
from odoo.addons.web.controllers.main import clean_action
from odoo.tools import date_utils


class AnalyticCashflowReport(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'phi_cash_flow.analytic.cashflow.report'
    _description = 'Cash Flow Report'

    # the line with this id will contain analytic accounts without a group
    DUMMY_GROUP_ID = 'group_for_accounts_with_no_group'

    # filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_date = None
    filter_analytic = False
    filter_hierarchy = False
    filter_unfold_all = None

    def _get_monthlist(self, date_start, date_end):
        total_months = lambda dt: dt.month + 12 * dt.year
        mlist = []
        for tot_m in range(total_months(date_start) - 1, total_months(date_end) ):
            y, m = divmod(tot_m, 12)
            mlist.append(date_utils.end_of(datetime.datetime(y, m + 1, 1), "month"))
        return mlist

    def _get_columns_name(self, options):
        analytic_entries_domain = self._generate_domain(options)
        month_list = self._get_month_list(analytic_entries_domain)

        analytic_account = self.env["account.analytic.account"].browse(self._get_analytic_accounts_ids())
        text = 'Compte analytique : %s' % (analytic_account[0].name) if len(analytic_account) else ''

        columns = [{'name': ''}, {'name': text}, {'name': ''}]
        for month in month_list:
            columns.append({'name': month.strftime("%b-%y"), 'class': 'number'})

        columns.append({'name': 'Total', 'class': 'number'})
        return columns

    def _get_month_list(self, analytic_entries_domain):
        months = self.env['phi_cash_flow.cash.flow'].search(analytic_entries_domain).mapped('date_end_month')
        if not len(months):
            return []
        date_start = min(months)
        date_end = max(months)
        month_list = self._get_monthlist(date_start, date_end)
        return month_list

    @api.model
    def _get_report_name(self):
        return _('Analytic Report')

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
        options = super(AnalyticCashflowReport, self)._get_options(previous_options)
        options['analytic_accounts'] = self._get_analytic_accounts_ids()
        options['analytic'] = False
        return options

    def _generate_analytic_account_lines(self, options):
        lines = []

        analytic_entries_domain = self._generate_domain(options)

        month_list = self._get_month_list(analytic_entries_domain)
        if not len(month_list):
            return lines

        analytic_entries = self.env['phi_cash_flow.cash.flow'].search(analytic_entries_domain)

        columns = [{'name': 'Prévisionnel', 'class': "o_account_reports_level0"}, {'name': '', 'colspan': 99}]
        lines.append({
                'id': 'blank_1',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })
        analytic_entries_domain_forecast = analytic_entries.filtered(lambda line: line.move_type == 'forecast')
        columns_analytic_entries_domain_forecast = self._get_line_values('forecast_in', analytic_entries_domain_forecast, month_list)
        lines.append({
                'id': 'forecast_in',
                'columns': columns_analytic_entries_domain_forecast,
                'unfoldable': False,
                'unfolded': False,
            })
        columns = self._get_line_values('forecast_out', analytic_entries_domain_forecast, month_list)
        lines.append({
                'id': 'forecast_out',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        columns_forecast_balance = self._get_line_values('forecast_balance', analytic_entries_domain_forecast, month_list)
        lines.append({
                'id': 'forecast_balance',
                'columns': columns_forecast_balance,
                'unfoldable': False,
                'unfolded': False,
            })

        if not any(analytic_entries.filtered(lambda line: line.move_type == 'real')):
            return lines

        columns = [{'name': 'Réalisé', 'class': "o_account_reports_level0"}, {'name': '', 'colspan': 99}]
        lines.append({
                'id': 'blank_1',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        columns = [{'name': ''}, {'name': 'CASH IN', 'class': "o_account_reports_level1", 'colspan': 99}]
        lines.append({
                'id': 'CASH IN',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        orders = analytic_entries.filtered(lambda line: line.move_type == 'real' and line.sale_id ).mapped('sale_id')
        for order in orders:
            columns = self._get_line_values('real_orders', order.cash_flow, month_list)
            lines.append({
                    'id': 'real_in_order_%s' % order.name,
                    'columns': columns,
                    'unfoldable': False,
                    'unfolded': False,
                })

        invoices = analytic_entries.filtered(lambda line: line.move_type == 'real' and line.invoice_id and line.amount_in).mapped('invoice_id')
        for invoice in invoices:
            columns = self._get_line_values('real_invoices', invoice.cash_flow, month_list)
            lines.append({
                    'id': 'real_in_invoice_%s' % invoice.name,
                    'columns': columns,
                    'unfoldable': False,
                    'unfolded': False,
                })

        analytic_entries_domain_real_in = analytic_entries.filtered(lambda line: line.move_type == 'real' and line.amount_in)
        columns_analytic_entries_domain_real_in = self._get_line_values('real_in_total', analytic_entries_domain_real_in, month_list)
        lines.append({
                'id': 'Total_CASH_IN',
                'columns': columns_analytic_entries_domain_real_in,
                'unfoldable': False,
                'unfolded': False,
            })

        analytic_entries_domain_real_in_forecast = analytic_entries.filtered(lambda line: line.sale_id or (line.move_type == 'forecast' and line.balance > 0))
        columns = self._get_line_values('real_in_total_forecast', analytic_entries_domain_real_in_forecast, month_list)
        lines.append({
                'id': 'Total_CASH_IN_forecast',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        columns = self._get_line_values('real_in_total_forecast_sum', analytic_entries_domain_real_in_forecast, month_list)
        lines.append({
                'id': 'Total_CASH_IN_forecast_sum',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        columns = [{'name': ''}, {'name': 'CASH OUT', 'class': "o_account_reports_level1", 'colspan': 99}]
        lines.append({
                'id': 'CASH OUT',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        orders = analytic_entries.filtered(lambda line: line.purchase_id != False).mapped('purchase_id')
        for order in orders:
            columns = self._get_line_values('real_out_orders', analytic_entries.filtered(lambda line: line.purchase_id.id == order.id), month_list)
            lines.append({
                    'id': 'real_out_order_%s' % order.name,
                    'columns': columns,
                    'unfoldable': False,
                    'unfolded': False,
                })

        analytic_entries_domain_real_out = analytic_entries.filtered(lambda line: line.purchase_id)
        columns_analytic_entries_domain_real_out = self._get_line_values('real_out_total', analytic_entries_domain_real_out, month_list)
        lines.append({
                'id': 'Total_CASH_OUT',
                'columns': columns_analytic_entries_domain_real_out,
                'unfoldable': False,
                'unfolded': False,
            })

        analytic_entries_domain_real_out_forecast = analytic_entries.filtered(lambda line: line.purchase_id or (line.move_type == 'forecast' and line.balance < 0))
        columns = self._get_line_values('real_out_total_forecast', analytic_entries_domain_real_out_forecast, month_list)
        lines.append({
                'id': 'Total_CASH_out_forecast',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        columns = self._get_line_values('real_out_total_forecast_sum', analytic_entries_domain_real_out_forecast, month_list)
        lines.append({
                'id': 'Total_CASH_OUT_forecast_sum',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        columns = [{'name': ''}, {'name': 'Solde', 'class': "o_account_reports_level1", 'colspan': 99}]
        lines.append({
                'id': 'Solde',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        analytic_entries_domain_real = analytic_entries.filtered(lambda line: line.move_type != 'forecast')
        columns = self._get_line_values('real_in_out', analytic_entries_domain_real, month_list)
        lines.append({
                'id': 'Total_CASH_in_out',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })

        columns = self._get_line_values('real_in_out_sum', analytic_entries_domain_real, month_list)
        lines.append({
                'id': 'Total_CASH_in_out_sum',
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            })
        return lines

    def _get_line_values(self, type_line, analytic_entries, month_list):
        columns = []
        mode = 'simple'
        if type_line == 'forecast_in':
            columns = [{'name': ''}, {'name': 'Entrées prévisionnelles'}]
            field = 'amount_in'
            field_class = 'number'
        elif type_line == 'forecast_out':
            columns = [{'name': ''}, {'name': 'Sorties prévisionnelles'}]
            field = 'amount_out'
            field_class = 'number'
        elif type_line == 'forecast_balance':
            columns = [{'name': ''}, {'name': 'Ecart', 'class': "o_account_reports_level2"}]
            field = 'balance'
            field_class = "number o_account_reports_level2"
            mode = 'progressive'
        elif type_line == 'real_orders':
            columns = [{'name': ''}, {'name': analytic_entries[0].sale_id.name}]
            field = 'balance'
            field_class = 'number'
        elif type_line == 'real_invoices':
            columns = [{'name': ''}, {'name': analytic_entries[0].invoice_id.name}]
            field = 'balance'
            field_class = 'number'
        elif type_line == 'real_in_total':
            columns = [{'name': ''}, {'name': 'Total CASH IN cumulé', 'class': "o_account_reports_level2"}]
            field = 'balance'
            field_class = 'number o_account_reports_level2'
            mode = 'progressive'
        elif type_line == 'real_in_total_forecast':
            columns = [{'name': ''}, {'name': 'Ecart CASH IN / Prévisionnel', 'class': "o_account_reports_level2"}]
            field = 'balance_real_previsionnal'
            field_class = 'number o_account_reports_level2'
        elif type_line == 'real_in_total_forecast_sum':
            columns = [{'name': ''}, {'name': 'Ecart CASH IN / Prévisionnel cumulé', 'class': "o_account_reports_level2"}]
            field = 'balance_real_previsionnal'
            field_class = 'number o_account_reports_level2'
            mode = 'progressive'
        elif type_line == 'real_out_orders':
            columns = [{'name': ''}, {'name': analytic_entries[0].purchase_id.name}]
            field = 'balance'
            field_class = 'number'
        elif type_line == 'real_out_total':
            columns = [{'name': ''}, {'name': 'Total CASH OUT cumulé', 'class': "o_account_reports_level2"}]
            field = 'balance'
            field_class = 'number o_account_reports_level2'
            mode = 'progressive'
        elif type_line == 'real_out_total_forecast':
            columns = [{'name': ''}, {'name': 'Ecart  CASH OUT / Prévisionnel', 'class': "o_account_reports_level2"}]
            field = 'balance_real_previsionnal'
            field_class = 'number o_account_reports_level2'
        elif type_line == 'real_out_total_forecast_sum':
            columns = [{'name': ''}, {'name': 'Ecart CASH OUT / Prévisionnel cumulé', 'class': "o_account_reports_level2"}]
            field = 'balance_real_previsionnal'
            field_class = 'number o_account_reports_level2'
            mode = 'progressive'
        elif type_line == 'real_in_out':
            columns = [{'name': ''}, {'name': 'Ecart CASH IN / CASH OUT', 'class': "o_account_reports_level2"}]
            field = 'balance'
            field_class = 'number o_account_reports_level2'
        elif type_line == 'real_in_out_sum':
            columns = [{'name': ''}, {'name': 'Ecart CASH IN / CASH OUT cumulé', 'class': "o_account_reports_level2"}]
            field = 'balance'
            field_class = 'number o_account_reports_level2'
            mode = 'progressive'
        else:
            columns = [{'name': 'Unknow', 'colspan': 99}]

        total_amount = 0.0
        for month in month_list:
            amount = sum(analytic_entries.filtered(lambda line: line.date_end_month == month.date()).mapped(field))
            total_amount += amount
            if mode == 'progressive':
                columns.append({'name': self.format_value(total_amount) if total_amount else '', 'class': field_class})
            else:
                columns.append({'name': self.format_value(amount) if amount else '', 'class': field_class})

        columns.append({'name': self.format_value(total_amount) if total_amount else '', 'class': field_class})
        return columns

    @api.model
    def _get_lines(self, options, line_id=None):
        return self._generate_analytic_account_lines(options)

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

