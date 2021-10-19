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
        res = self._check_approval(model, res_id, method, action_id)
        if not res.get("approved"):
            rule = self.env['studio.approval.rule'].browse(res["rules"][0]['id'])
            if rule:
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', res_id),
                    ('res_model_id', '=', rule.model_id.id),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                    ('rule_approval', '=', rule.id)])
                if not existing_activity:
                    if len(rule.group_id.users):
                        self.env['mail.activity'].create({
                            'summary': rule.message,
                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                            'res_model_id': rule.model_id.id,
                            'res_id': res_id,
                            'user_id': rule.group_id.users[0].id,
                            'rule_approval': rule.id,
                        })
        else:
            if res.get("rules"):
                rule = self.env['studio.approval.rule'].browse(res["rules"][0]['id'])
                if rule:
                    existing_activity = self.env['mail.activity'].search([
                        ('res_id', '=', res_id),
                        ('res_model_id', '=', rule.model_id.id),
                        ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                        ('summary', '=', rule.message)])
                if existing_activity:
                    existing_activity._action_done()

        return res

    def unlink_approval_user(self, user_id, res_id, model_name):
        existing_entry = self.env['studio.approval.entry'].search([
            ('model', '=', model_name),
            ('method', '=', self.method), ('action_id', '=', self.action_id.id),
            ('res_id', '=', res_id), ('rule_id', '=', self.id)])
        existing_entry.unlink()

    @api.model
    def _check_approval(self, model, res_id, method, action_id):
        self = self._clean_context()
        if method and action_id:
            raise UserError(_('Approvals can only be done on a method or an action, not both.'))
        record = self.env[model].browse(res_id)
        # we check that the user has write access on the underlying record before doing anything
        # if another type of access is necessary to perform the action, it will be checked
        # there anyway
        record.check_access_rights('write')
        record.check_access_rule('write')
        ruleSudo = self.sudo()
        domain = self._get_rule_domain(model, method, action_id)
        # order by 'exclusive_user' so that restrictive rules are approved first
        rules_data = ruleSudo.search_read(
            domain=domain,
            fields=['group_id', 'message', 'exclusive_user', 'domain', 'can_validate'],
            order='exclusive_user desc, id asc'
        )
        applicable_rule_ids = list()
        for rule in rules_data:
            rule_domain = rule.get('domain') and literal_eval(rule['domain'])
            if not rule_domain or record.filtered_domain(rule_domain):
                # the record matches the domain of the rule
                # or the rule has no domain set on it
                applicable_rule_ids.append(rule['id'])
        rules_data = list(filter(lambda r: r['id'] in applicable_rule_ids, rules_data))
        if not rules_data:
            # no rule matching our operation: return early, the user can proceed
            return {'approved': True, 'rules': [], 'entries': []}
        # need sudo, we need to check entries from other people and through record rules
        # users can only see their own entries by default
        entries_data = self.env['studio.approval.entry'].sudo().search_read(
            domain=[('model', '=', model), ('res_id', '=', res_id), ('rule_id', 'in', applicable_rule_ids)],
            fields=['approved', 'rule_id', 'user_id'])
        entries_by_rule = dict.fromkeys(applicable_rule_ids, False)
        for rule_id in entries_by_rule:
            candidate_entry = list(filter(lambda e: e['rule_id'][0] == rule_id, entries_data))
            candidate_entry = candidate_entry and candidate_entry[0]
            if not candidate_entry:
                # there is a rule that has no entry yet, try to approve it
                try:
                    rule = self.env['studio.approval.rule'].browse(rule_id)
                    if self.env.user not in rule.group_id.users:
                        new_entry = self.browse(rule_id)._set_approval(res_id, True)
                        entries_data.append({
                            'id': new_entry.id,
                            'approved': True,
                            'rule_id': [rule_id, False],
                            'user_id': self.env.user.name_get()[0]
                        })
                    entries_by_rule[rule_id] = True
                except UserError:
                    # either the user doesn't have the required group, or they already
                    # validated another rule for a 'exclusive_user' approval
                    # nothing to do here
                    pass
            else:
                entries_by_rule[rule_id] = candidate_entry['approved']
        return {
            'approved': all(entries_by_rule.values()),
            'rules': rules_data,
            'entries': entries_data,
        }