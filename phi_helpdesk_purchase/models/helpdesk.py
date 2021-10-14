# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', domain="['|', (not commercial_partner_id, '=', 1), ('partner_id', 'child_of', commercial_partner_id or []), ('company_id', '=', company_id)]", index=True)
