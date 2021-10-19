# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    incoterm_description = fields.Text("Incoterm Description")
    incoterm_full_name = fields.Char(compute="_compute_incoterm_full_name")

    def _compute_incoterm_full_name(self):
        for invoice in self:
            if not invoice.invoice_incoterm_id:
                invoice.incoterm_full_name = False
            else:
                invoice.incoterm_full_name = "\n".join([invoice.invoice_incoterm_id.code, invoice.incoterm_description])
