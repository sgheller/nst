# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PurchaseCategory(models.Model):
    _name = 'phi_purchase_category.purchase_category'
    _description = 'Purchase Category'
    _order = "name"

    name = fields.Char(string="Purchase Category", required=True)
    description = fields.Text('Description')
