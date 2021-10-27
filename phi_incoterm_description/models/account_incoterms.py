# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountIncoterms(models.Model):
    _inherit = 'account.incoterms'

    is_additionnal_info = fields.Boolean("Nedd additionnal informations", compute="_compute_is_additionnal_info")

    def _compute_is_additionnal_info(self):
        for incoerm in self:
            if incoerm.code in ('FAS', 'FOB', 'CFR', 'CIF', 'CPT', 'CIP'):
                incoerm.is_additionnal_info = True
            else:
                incoerm.is_additionnal_info = False

    def get_additionnal_informations(self, start_adddress, end_address):
        self.ensure_one()
        desciption = False
        if self.code in ('EXW', 'FCA'):
            if start_adddress:
                if start_adddress.city and start_adddress.zip and start_adddress.country_id:
                    desciption = ", ".join([start_adddress.city, start_adddress.zip, start_adddress.country_id.name])
        if self.code in ('DPU', 'DAP', 'DDP'):
            if end_address:
                if end_address.city and end_address.zip and end_address.country_id:
                    desciption = ", ".join([end_address.city, end_address.zip, end_address.country_id.name])
        return desciption
