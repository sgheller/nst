# -*- coding: utf-8 -*-

from odoo import models, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        res_ids = self._context.get('active_ids')
        invoices = self.env['account.move'].browse(res_ids)
        for invoice in invoices:
            if invoice.payment_method:
                res["journal_id"] = invoice.payment_method
                break
        return res
