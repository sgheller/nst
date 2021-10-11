# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging
import pytz

from odoo import api, exceptions, fields, models, _
from odoo.osv import expression

from odoo.tools.misc import clean_context
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    rule_approval = fields.Many2one('studio.approval.rule')
    rule_approval_type = fields.Selection(selection=[
        ('ask', 'Ask'),
        ('approved', 'Approved'),
        ('refused', 'Refused')
    ], default='ask')

    def action_done(self):
        res = super(MailActivity, self).action_done()
        return res

    def action_feedback(self, feedback=False, attachment_ids=None):
        if self.rule_approval:
            if self.rule_approval_type == 'ask':
                # Approve rule
                self.rule_approval.set_approval(self.res_id, True)
                # Execute action
                if self.rule_approval.method:
                    rule_object = self.env[self.rule_approval.model_name]
                    if hasattr(rule_object, self.rule_approval.method):
                        rule_object_id = rule_object.browse(self.res_id)
                        getattr(rule_object_id, self.rule_approval.method)()
                        # delete approbation
                        self.rule_approval.unlink_approval_user(self.create_uid, self.res_id, self.rule_approval.model_name)
                else:
                    self.env['mail.activity'].create({
                        'summary': 'Approuvé : ' + self.summary if self.summary else '',
                        'activity_type_id': self.activity_type_id.id,
                        'res_model_id': self.res_model_id.id,
                        'res_id': self.res_id,
                        'user_id': self.create_uid.id,
                        'rule_approval': self.rule_approval.id,
                        'rule_approval_type': 'approved',
                        'note': feedback,
                    })
        res = super(MailActivity, self).action_feedback(feedback, attachment_ids)
        return res

