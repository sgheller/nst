# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2020-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import fields, models


class ApproveProduct(models.Model):
    _inherit = 'product.template'

    approve_state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], default='draft', copy=False)

    def confirm_product_approval(self):
        for rec in self:
            rec.approve_state = 'confirmed'

    def reset_product_approval(self):
        for rec in self:
            rec.approve_state = 'draft'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_id = fields.Many2one(
        'product.product', string='Product',
        domain="[('approve_state', '=', 'confirmed'), ('sale_ok', '=', True), '|', ('company_id', '=', False),('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_id = fields.Many2one('product.product', string='Product', domain=[('approve_state', '=', 'confirmed'), ('purchase_ok', '=', True)], change_default=True)