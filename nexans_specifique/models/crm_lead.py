
from odoo import models, fields, api, _


class CrmLead(models.Model):
    
    _inherit = 'crm.lead'

    account_analytic_id = fields.Many2one('account.analytic.account', string='Compte Analytique', store=True, readonly=True)
    stage_id = fields.Many2one(
        'crm.stage', string='Stage', index=True, tracking=True,
        compute='_compute_stage_id', readonly=True, store=True,
        copy=False, group_expand='_read_group_stage_ids', ondelete='restrict',
        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]")

    def action_previous(self):
        self.ensure_one()
        previous_stage_id = self.env['crm.stage'].search(['|', ('team_id', '=', False), ('team_id', '=', self.team_id.id), ('sequence', '<', self.stage_id.sequence)],
                                                     order='sequence desc', limit=1)
        if previous_stage_id:
            self.stage_id = previous_stage_id
        pass

    def action_next(self):
        self.ensure_one()
        next_stage_id = self.env['crm.stage'].search(['|', ('team_id', '=', False), ('team_id', '=', self.team_id.id), ('sequence', '>', self.stage_id.sequence)],
                                                     order='sequence', limit=1)
        if next_stage_id:
            self.stage_id = next_stage_id

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

    def action_archive(self):
        res = super(CrmLead, self).action_archive()
        for lead in self:
            if lead.account_analytic_id:
                if not any(lead.account_analytic_id.cash_flow.filtered(lambda line: line.move_type == 'real')):
                    lead.account_analytic_id.action_archive()
        return res

    def toggle_active(self):
        super(CrmLead, self).toggle_active()
        for lead in self:
            if lead.account_analytic_id and not lead.account_analytic_id.active:
                lead.account_analytic_id.toggle_active()