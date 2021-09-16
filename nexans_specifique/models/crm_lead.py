
from odoo import models, fields, api, _


class CrmLead(models.Model):
    
    _inherit = 'crm.lead'

    account_analytic_id = fields.Many2one('account.analytic.account', string='Compte Analytique', store=True, readonly=True)

    def write(self, values):
        if not self.account_analytic_id and values.get('account_analytic_id') == None:
            analytic_account_id = self.env['account.analytic.account'].create({'name': self.name, 'partner_id': self.partner_id.id})
            values["account_analytic_id"] = analytic_account_id.id
        res = super(CrmLead, self).write(values)
        if self.account_analytic_id and not self.account_analytic_id.partner_id and self.partner_id:
            self.account_analytic_id.write({'partner_id': self.partner_id.id})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('account_analytic_id'):
                analytic_account_id = self.env['account.analytic.account'].create({'name': vals.get('name'), 'partner_id': vals.get('partner_id')})
                vals['account_analytic_id'] = analytic_account_id.id
        leads = super(CrmLead, self).create(vals_list)

        return leads