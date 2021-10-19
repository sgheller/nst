# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    purchase_category_id = fields.Many2one('phi_purchase_category.purchase_category', string='Purchase Category')
