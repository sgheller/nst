# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import collections
from odoo import api

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = "project.project"

    def write(self, values):
        if not self.analytic_account_id and values.get('analytic_account_id') == None:
            analytic_account_id = self.env['account.analytic.account'].create({'name': self.name, 'partner_id': self.partner_id.id})
            values["analytic_account_id"] = analytic_account_id.id
        res = super(ProjectProject, self).write(values)
        return res

    @api.model
    def create(self, vals):
        if not vals.get('analytic_account_id'):
            analytic_account_id = self.env['account.analytic.account'].create({'name': vals.get('name'), 'partner_id': vals.get('partner_id')})
            vals['analytic_account_id'] = analytic_account_id.id
        return super(ProjectProject, self).create(vals)
