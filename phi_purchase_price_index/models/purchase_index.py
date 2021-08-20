# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta, datetime
from odoo.exceptions import UserError


class PurchaseIndex(models.Model):
    _name = 'phi_purchase_price_index.purchase.index'
    _description = 'indices'
    _order = "date_from desc"
    _rec_name = 'date_from'

    date_from = fields.Date(string="Date", required=True)
    index_meps = fields.Integer(string="MEPS", help="Indice matière premières", default=0)
    index_mo = fields.Integer(string="MO", help="Indice main d'oeuvre", default=0)
    index_lme = fields.Integer(string="LME", help="Indice traitement de surface", default=0)

    state = fields.Selection([('draft', 'Brouillon'), ('done', 'Traité')], 'Statut', readonly=True, copy=False, default='draft', required=True)

    _sql_constraints = [
        ('unique_date', 'unique (date_from)', 'La date doit être unique')
    ]

    @api.model
    def create(self, vals):
        index_draft = self.env["phi_purchase_price_index.purchase.index"].search([('state', '=', 'draft')])
        if len(index_draft) > 0:
            raise UserError(_('Il existe un autre index en brouillon, vous devez le valider avant de créer un nouvel index.'))
        current_index = self._get_current_index()
        if current_index.date_from > datetime.strptime(vals["date_from"], '%Y-%m-%d').date():
            raise UserError(_("Vous devez créer un index avec une date supérieure à l'index en cours % s" % current_index.date_from))
        return super(PurchaseIndex, self).create(vals)

    def unlink(self):
        if self.state == 'done':
            raise UserError(_('Vous ne pouvez pas supprimer un index validé'))
        return super(PurchaseIndex, self).unlink()

    def _select_seller_for_index(self, product_id, date):
        res = self.env['product.supplierinfo']
        sellers = product_id.seller_ids.filtered(lambda s: s.name.active).sorted(lambda s: (s.sequence, -s.min_qty, s.price, s.id))
        sellers = sellers.filtered(lambda s: not s.company_id or s.company_id.id == self.env.company.id)
        for seller in sellers:
            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if seller.product_id and seller.product_id != product_id:
                continue
            res |= seller
        return res

    def _calculate_price_index(self, seller):
        if seller.purchase_index_id:
            return self._calculate_index_evolution(seller, self)
        else:
            return seller.price

    @staticmethod
    def _calculate_index_evolution(seller_from, index_to, index_from=False):
        if not index_from:
            index_from = seller_from.purchase_index_id
        if not index_from or not index_to:
            return seller_from.price
        part_meps = seller_from.price * seller_from.portion_meps / 100 / index_from.index_meps * index_to.index_meps
        part_mo = seller_from.price * seller_from.portion_mo / 100 / index_from.index_mo * index_to.index_mo
        part_lme = seller_from.price * seller_from.portion_lme / 100 / index_from.index_lme * index_to.index_lme

        return part_meps + part_mo + part_lme

    def _get_current_index(self, date=None):
        if date is None:
            date = fields.Date.context_today(self)
        return self.env["phi_purchase_price_index.purchase.index"].search([('date_from', '<=', date),('state', '=', 'done')], order='date_from desc', limit=1)

    def action_apply(self):
        products_index = self.env["product.template"].search([('purchase_price_index', '=', True)])
        for product in products_index:
            new_cost = 0
            sellers = self._select_seller_for_index(product, self.date_from)
            for seller in sellers:
                new_price = self._calculate_price_index(seller)
                seller.copy({
                    'purchase_index_id': self.id,
                    'price': new_price,
                    'date_start': self.date_from,
                    'date_end': False,
                })
                if not seller.date_end or seller.date_end >= self.date_from:
                    seller.date_end = self.date_from - timedelta(days=1)
                # Nouveau Cout
                if self.env.company.currency_id != seller.currency_id:
                    new_price = seller.currency_id._convert(new_price, self.env.company.currency_id, self.env.company, self.date_from)

                if seller.min_qty <= 1 and new_cost < new_price:
                    new_cost = new_price

            if new_cost and product.categ_id.property_cost_method == 'standard':
                if product.uom_id != product.uom_po_id:
                    new_cost = product.uom_po_id._compute_price(new_cost, product.uom_id)
                product.standard_price = new_cost

        self.state = 'done'


