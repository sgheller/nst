# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    payment_method = fields.Many2one('account.journal', string="Payment method", domain=[('type', 'in', ('cash', 'bank'))])