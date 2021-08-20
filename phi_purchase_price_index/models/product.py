# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchase_price_index = fields.Boolean(string="Prix Achat Indicaire", default=False)


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    portion_meps = fields.Float(string="MEPS %", help="Indice matière premières", default=0, copy=True)
    portion_mo = fields.Float(string="MO %", help="Indice main d'oeuvre", default=0, copy=True)
    portion_lme = fields.Float(string="LME %", help="Indice traitement de surface", default=0, copy=True)

    purchase_price_index = fields.Boolean(related="product_tmpl_id.purchase_price_index", store=True)

    purchase_index_id = fields.Many2one('phi_purchase_price_index.purchase.index', string="Index Achat")

    _sql_constraints = [
        ('check_portions_total', 'CHECK((portion_meps + portion_mo + portion_lme) = 100 and purchase_price_index = true)', 'Le total des indices doit faire 100'),
    ]

    @api.model
    def create(self, vals):
        if vals.get("product_tmpl_id") and not vals.get("purchase_index_id"):
            product = self.env["product.template"].browse(vals["product_tmpl_id"])
            if product and product.purchase_price_index:
                date = None
                if vals.get("date_start"):
                    date = vals["date_start"]
                index = self.env["phi_purchase_price_index.purchase.index"]._get_current_index(date)
                if index:
                    vals["purchase_index_id"] = index.id
                else:
                    raise UserError(_('Aucun index validé trouvé'))

        res = super(SupplierInfo, self).create(vals)

        return res



