# -*- coding:utf-8 -*-

import base64
import io
from odoo import fields, models, _
import logging
import itertools

_logger = logging.getLogger(__name__)


def compute_account_code(account_lines):
    if account_lines[0].account_id.user_type_id.type == 'receivable' and account_lines[0].partner_id.quadra_customer_ref:
        return account_lines[0].partner_id.quadra_customer_ref
    elif account_lines[0].account_id.user_type_id.type == 'payable' and account_lines[0].partner_id.quadra_supplier_ref:
        return account_lines[0].partner_id.quadra_supplier_ref
    elif account_lines[0].account_id.user_type_id.type in ['receivable', 'payable'] and account_lines[0].partner_id.ref:
        return account_lines[0].partner_id.ref
    else:
        return account_lines[0].account_id.code


def get_amount(account_lines):
    return round((sum(account_lines.mapped('debit')) - sum(account_lines.mapped('credit'))) * 100)


def compute_amount(account_lines):
    amount = abs(get_amount(account_lines))
    return "+" + str(amount).zfill(12)


def compute_name(account_lines):
    account_line = account_lines[0]
    if not account_line.company_id.quadra_export_group_lines:
        return account_line.name
    else:
        return "%s - %s" % (
            account_line.ref or account_line.move_id.name,
            account_line.partner_id.name if account_line.partner_id else ""
        )



QUADRA_ASCII_FORMAT = {  # Quadra name: [Position, Length, required, lambda expr to get value from move line, lambda expr to get value from journal]
    "Type": [1, 1, True, lambda l: "M"],
    "Numéro de compte": [2, 8, True, compute_account_code],
    "Code journal": [10, 2, True, lambda l: l[0].journal_id.code],
    "N° folio": [12, 3, True, lambda l: "000"],
    "Date écriture": [15, 6, True, lambda l: l[0].date.strftime("%d%m%y") if not l[0].company_id.quadra_export_group_lines else l[0].move_id.date.strftime("%d%m%y")],
    "Code libellé": [21, 1, False, False],
    "Libellé libre": [22, 20, False, False],     # name (set in pos 117 on 30 characters)
    "Sens Débit/Crédit": [42, 1, True, lambda l: "D" if get_amount(l) > 0 else "C"],
    "Montant en centimes signé": [43, 13, True, compute_amount],
    "Compte de contrepartie": [56, 8, False, False],
    "Date échéance": [64, 6, False, lambda l: min(l.mapped('date_maturity')).strftime("%d%m%y") if l.mapped('date_maturity') else ''],
    "Code lettrage": [70, 2, False, lambda l: l[0].full_reconcile_id.name if not l[0].company_id.quadra_export_group_lines and l[0].full_reconcile_id else ""],
    "Code statistiques": [72, 3, False, False],
    "N° de pièce": [75, 5, False, lambda l: str(l[0].move_id.id)],
    "Code affaire": [80, 10, False, False],
    "Quantité 1": [90, 10, False, lambda l: str(l[0].quantity) if not l[0].company_id.quadra_export_group_lines else ""],
    "Numéro de pièce": [100, 8, False, lambda l: l[0].move_id.name.replace('/', '')[-8:]],
    "Code devise": [108, 3, False, lambda l: l[0].currency_id.name],
    "Code journal 2": [111, 3, True, lambda l: l[0].journal_id.code],
    "Flag Code TVA": [114, 1, False, False],
    "Méthode de calcul TVA": [115, 1, False, False],
    "Code TVA": [116, 1, False, False],
    "Libellé écriture": [117, 30, False, compute_name],
    "Code TVA 2": [147, 2, False, False],
    "N° de pièce alpha": [149, 10, False, lambda l: l[0].move_id.name.replace('/', '')[-10:]],
    "Reservé": [159, 10, False, False],
    "Montant dans la devise": [169, 13, False, False],
    "Pièce jointe à l'écriture": [182, 12, False, False],
    "Quantité 2": [194, 10, False, False],
    "NumUniq": [204, 10, False, False],              # Export only
    "Code opérateur": [214, 4, False, False],        # Export only
    "Date système": [218, 14, False, False],         # Export only
}


class ExportASCII(models.TransientModel):
    _name = 'account.export_ascii'
    _description = 'Export ASCII for Quadra'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.today())
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.today())
    journal_id = fields.Many2one('account.journal', string="Journal")
    file = fields.Binary('File', readonly=True)
    filename = fields.Char(string='Filename', readonly=True)
    warning_msg = fields.Html(string='Warning', readonly=True)

    def check_before_generate(self, move_lines):
        lines_without_aux_num = move_lines\
            .filtered(lambda l: l.account_id.user_type_id.type in ['receivable', 'payable'] and compute_account_code([l]) == l.account_id.code)
        if lines_without_aux_num:
            self.warning_msg = "<b>" + _("Missing Aux Num on Partners:") + "</b><br/>" + "<br/>"\
                .join(lines_without_aux_num.mapped('partner_id.name')) + \
                "<br/><b>Account code will be used instead.</b>"

    def generate_file(self):
        content = ""
        company = self.env.user.company_id
        search_domain = [
            ('company_id', '=', company.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.journal_id:
            search_domain.append(('journal_id', '=', self.journal_id.id))
        move_lines = self.env['account.move.line'].search(search_domain)

        self.check_before_generate(move_lines)

        for k, grouped_lines in itertools.groupby(move_lines, lambda l: [l.partner_id, l.account_id, l.move_id] if company.quadra_export_group_lines else l):
            grouped_lines = self.env['account.move.line'].browse([l.id for l in list(grouped_lines)])
            line = io.StringIO()
            for key, item_val in QUADRA_ASCII_FORMAT.items():
                pos, length, required, expr = item_val
                line.seek(pos-1)
                value = ""
                if expr:
                    try:
                        value = (expr(grouped_lines) or "").encode(encoding='ascii', errors='replace').decode()
                    except Exception:
                        value =''
                if len(value) > length:
                    _logger.warning('Content cropped for field %s: "%s"' % (key, value))
                    value = value[:length]
                if not value and required:
                    _logger.error('Required field not filled for field %s' % key)
                line.write(value.replace('\n', '').ljust(length))
            line.seek(0)
            content += line.read() + '\n'

        self.write({
            'file': base64.b64encode(content.encode(encoding='ascii', errors='replace')),
            'filename': '%s-ASCII-%s-%s.txt' % (
                company.vat[4:13] if company.vat else "",
                fields.Date.to_string(self.date_from).replace('-', ''),
                fields.Date.to_string(self.date_to).replace('-', ''),
            )
        })

        return {
            'name': _('ASCII File Download'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.export_ascii',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('phi_quadra_export.account_export_ascii_result_form_view').id,
            'res_id': self.id,
            'target': 'new',
        }

