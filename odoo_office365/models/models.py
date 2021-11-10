# -*- coding: utf-8 -*-

import logging
import re

from odoo import fields, models, api, osv
from odoo.exceptions import ValidationError

from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
from odoo.exceptions import UserError, AccessError
import requests
import json
from datetime import datetime
import time
from datetime import timedelta

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/]{3,}=*)([\'"])', re.I)


class CustomUser(models.Model):
    _inherit = 'res.users'

    code = fields.Char('code')
    token = fields.Char('Token', readonly=True)
    refresh_token = fields.Char('Refresh Token', readonly=True)
    expires_in = fields.Char('Expires IN', readonly=True)


class CustomMeeting(models.Model):
    _inherit = 'calendar.event'

    office_id = fields.Char('Office365 Id')
    category_name = fields.Char('Categories', )
    is_update = fields.Boolean('Is Updated')
    modified_date = fields.Datetime('Modified Date')
    calendar_id = fields.Many2one(comodel_name="office.calendars", string="Office 365 Calendar Type", required=False, )
    show_as = fields.Selection(selection=[('free', 'Free'), ('busy', 'Busy'),
                                          ('tentative', 'Tentative'), ('workingElsewhere', 'Working Elsewhere'),
                                          ('oof', 'Out of Office')])


class CustomMessageInbox(models.Model):
    _inherit = 'mail.message'

    office_id = fields.Char('Office Id')


class CustomMessage(models.Model):
    _inherit = 'mail.mail'

    office_id = fields.Char('Office Id')

    @api.model
    def create(self, values):
        """
        overriding create message to send email on message creation
        :param values:
        :return:
        """
        ################## New Code ##################
        ################## New Code ##################
        o365_id = None
        conv_id = None
        context = self._context

        current_uid = context.get('uid')

        user = self.env['res.users'].browse(current_uid)
        if user.token:
            if user.expires_in:
                expires_in = datetime.fromtimestamp(int(user.expires_in) / 1e3)
                expires_in = expires_in + timedelta(seconds=3600)
                nowDateTime = datetime.now()
                if nowDateTime > expires_in:
                    self.generate_refresh_token()

            if 'mail_message_id' in values:
                email_obj = self.env['mail.message'].search([('id', '=', values['mail_message_id'])])
                partner_id = values['recipient_ids'][0][1]
                partner_obj = self.env['res.partner'].search([('id', '=', partner_id)])

                new_data = {
                            "subject": values['subject'] if values['subject'] else email_obj.body,
                            # "importance": "high",
                            "body": {
                                "contentType": "HTML",
                                "content": email_obj.body
                            },
                            "toRecipients": [
                                {
                                    "emailAddress": {
                                        "address": partner_obj.email
                                    }
                                }
                            ]
                        }

                response = requests.post(
                    'https://graph.microsoft.com/v1.0/me/messages', data=json.dumps(new_data),
                                        headers={
                                            'Host': 'outlook.office.com',
                                            'Authorization': 'Bearer {0}'.format(user.token),
                                            'Accept': 'application/json',
                                            'Content-Type': 'application/json',
                                            'X-Target-URL': 'http://outlook.office.com',
                                            'connection': 'keep-Alive'
                                        })
                if 'conversationId' in json.loads((response.content.decode('utf-8'))).keys():
                    conv_id = json.loads((response.content.decode('utf-8')))['conversationId']

                if 'id' in json.loads((response.content.decode('utf-8'))).keys():

                    o365_id = json.loads((response.content.decode('utf-8')))['id']
                    if email_obj.attachment_ids:
                        for attachment in self.getAttachments(email_obj.attachment_ids):
                            attachment_response = requests.post(
                                'https://graph.microsoft.com/beta/me/messages/' + o365_id + '/attachments',
                                data=json.dumps(attachment),
                                headers={
                                    'Host': 'outlook.office.com',
                                    'Authorization': 'Bearer {0}'.format(user.token),
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json',
                                    'X-Target-URL': 'http://outlook.office.com',
                                    'connection': 'keep-Alive'
                                })
                    send_response = requests.post(
                        'https://graph.microsoft.com/v1.0/me/messages/' + o365_id + '/send',
                        headers={
                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        })

                    message = super(CustomMessage, self).create(values)
                    # message.email_from = None

                    if conv_id:
                        message.office_id = conv_id

                    return message
                else:
                    pass
                    # print('Check your credentials! Mail does not send due to invlide office365 credentials ')

            else:

                return super(CustomMessage, self).create(values)

        else:
            # print('Office354 Token is missing.. Please add your account token and try again!')
            return super(CustomMessage, self).create(values)

    def getAttachments(self, attachment_ids):
        attachment_list = []
        if attachment_ids:
            # attachments = self.env['ir.attachment'].browse([id[0] for id in attachment_ids])
            attachments = self.env['ir.attachment'].search([('id', 'in', [i.id for i in attachment_ids])])
            for attachment in attachments:
                attachment_list.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": attachment.name,
                    "contentBytes": attachment.datas.decode("utf-8")
                })
        return attachment_list

    def generate_refresh_token(self):
        context = self._context
        current_uid = context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        redirect_url = IrConfigParameter.get_param('odoo_office365.redirect_url')
        client_id = IrConfigParameter.get_param('odoo_office365.client_id')
        client_secret = IrConfigParameter.get_param('odoo_office365.client_secret')
        header = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        payload = 'grant_type=refresh_token&refresh_token=' + user.refresh_token + \
                  '&redirect_uri=' + redirect_url + '&client_id=' + client_id + \
                  '&client_secret=' + client_secret
        response = requests.post(url, data=payload, headers=header)

        if response.status_code == 200:
            newToken = json.loads(response.content)
            user.write({
                'token': newToken['access_token'],
                'refresh_token': newToken['refresh_token'],
                'expires_in': int(round(time.time() * 1000))
            })
            self.env.cr.commit()
        else:
            raise ValidationError(str("Your Token has been expired and while updating automatically we are facing issue can you please "
                                      "check your credentials or again login with your Office 365 account"))


class CustomActivity(models.Model):
    _inherit = 'mail.activity'

    office_id = fields.Char('Office365 Id')
    is_update = fields.Boolean('Is Updated')
    modified_date = fields.Datetime('Modified Date')


class CustomContacts(models.Model):
    _inherit = 'res.partner'

    office_contact_id = fields.Char('Office365 Id')
    modified_date = fields.Datetime('Modified Date')
    location = fields.Char(string='Location')
    firstName = fields.Char(string='First Name')
    lastName = fields.Char(string='Last Name')
    middleName = fields.Char(string='Middle Name')
    is_update = fields.Boolean('Is Updated')


class ContactCateg(models.Model):
    _inherit = 'res.partner.category'

    categ_id = fields.Char(string="o_category id", required=False, )


class CalendarEventCateg(models.Model):
    _inherit = 'calendar.event.type'

    color = fields.Char(string="Color", required=False, )
    categ_id = fields.Char(string="o_category id", required=False, )