# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning


class ResPartner(models.Model):
    _inherit = "res.partner"

    quadra_customer_ref = fields.Char(
        'Customer Ref Quadra', help='Used for quadra ASCII export, if defined, used for receivable account type'
    )
    quadra_supplier_ref = fields.Char(
        'Supplier Ref Quadra', help='Used for quadra ASCII export, if defined, used for payable account type'
    )

    @api.onchange('quadra_customer_ref', 'quadra_supplier_ref')
    def check_quadra_ref_length(self):
        if self.quadra_customer_ref and len(self.quadra_customer_ref) > 8 or self.quadra_supplier_ref and len(self.quadra_supplier_ref) > 8:
            raise Warning(_("Quadra ASCII file doesn't support ref longer than 8 characters"))
