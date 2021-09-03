# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_prototype = fields.Boolean(string="Is prototype", defaul=False, store=True, readonly=False, help="This product is a prototype.")

    @api.onchange('is_prototype')
    def onchange_is_prototype(self):
        for product in self:
            if product.is_prototype:
                product.sale_ok = False
