# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, models, fields, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, AccessError, UserError


class StudioApprovalRule(models.Model):
    _inherit = "studio.approval.rule"

    @api.model
    def check_approval(self, model, res_id, method, action_id):
        res = super(StudioApprovalRule, self).check_approval(model, res_id, method, action_id)
        if not res.get("approved"):
            rule = self.env['studio.approval.rule'].browse(res["rules"][0]['id'])
            if rule:
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', res_id),
                    ('res_model_id', '=', rule.model_id.id),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                    ('summary', '=', rule.message)])
                if not existing_activity:
                    if len(rule.group_id.users):
                        self.env['mail.activity'].create({
                            'summary': rule.message,
                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                            'res_model_id': rule.model_id.id,
                            'res_id': res_id,
                            'user_id': rule.group_id.users[0].id
                        })

        return res

