# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_method = fields.Many2one('account.journal', string="Payment method", domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()
        if self.partner_id:
            self.payment_method = self.partner_id.payment_method
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            if partner.payment_method.id and not vals.get('payment_method'):
                vals['payment_method'] = partner.payment_method.id
        res = super(AccountMove, self).create(vals_list)
        return res