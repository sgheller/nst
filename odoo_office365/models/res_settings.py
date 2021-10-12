# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.http import request
import requests
import json
from odoo.exceptions import ValidationError, Warning, UserError


class Office365SettingModel(models.TransientModel):
    _inherit = 'res.config.settings'

    redirect_url = fields.Char(string='Redirect URL', compute='_get_current_url', config_parameter='odoo_office365.redirect_url')
    client_id = fields.Char(string='Client ID', config_parameter='odoo_office365.client_id')
    client_secret = fields.Char(string='Client Secret', config_parameter='odoo_office365.client_secret')
    login_url = fields.Char('Login URL', compute='_compute_url', config_parameter='odoo_office365.login_url')
    interval_number = fields.Integer(string="Interval Number", required=False, config_parameter='odoo_office365.interval_number')
    interval_unit = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit', config_parameter='odoo_office365.interval_unit')

    @api.depends('redirect_url', 'client_id', 'client_secret')
    def _compute_url(self):
        for i in self:
            i.login_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?' \
                             'client_id=%s&redirect_uri=%s&response_type=code&scope=openid+offline_access+' \
                             'Calendars.ReadWrite+Mail.ReadWrite+Mail.Send+User.ReadWrite+Tasks.ReadWrite+' \
                             'Contacts.ReadWrite+MailboxSettings.Read' % (
                                 i.client_id, i.redirect_url)

    @api.depends('client_id')
    def _get_current_url(self):
        for i in self:
            base_url = request.httprequest.url_root
            base_url = base_url[:4] + 's' + base_url[4:]
            i.redirect_url = base_url+'odoo'

    def get_log(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Office 365 Logs',
            'view_mode': 'tree',
            'res_model': 'sync.history',
            'context': "{'create': False}"
        }

    def set_values(self):
        res = super(Office365SettingModel, self).set_values()

        return res

    def generate_token(self, code):
        try:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            redirect_url = IrConfigParameter.get_param('odoo_office365.redirect_url')
            client_id = IrConfigParameter.get_param('odoo_office365.client_id')
            client_secret = IrConfigParameter.get_param('odoo_office365.client_secret')

            if not client_id or not redirect_url or not client_secret:
                ValidationError("Please ask Admin to add Office 365 credentials")

            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
            payload = 'grant_type=authorization_code&code=' + code + '&redirect_uri=' + redirect_url + '&client_id=' + client_id + '&client_secret=' + client_secret
            response = requests.post(url, data=payload, headers=header)
            data = {}
            if response.status_code == 200:
                response = json.loads(response.content)
                data['token'] = response['access_token']
                data['refresh_token'] = response['refresh_token']
                data['expires_in'] = response['expires_in']

                categoriesUrl = 'https://graph.microsoft.com/v1.0/me/outlook/masterCategories'
                newDataHeader = {
                    'Host': 'outlook.office.com',
                    'Authorization': 'Bearer {0}'.format(data['token']),
                    'Accept': 'application/json',
                    'X-Target-URL': 'http://outlook.office.com',
                    'connection': 'keep-Alive'
                }
                categoriesResponse = requests.get(categoriesUrl, headers=newDataHeader)
                if categoriesResponse.status_code == 200:
                    categories = json.loads(categoriesResponse.content)
                    self.createPartnerCategory(categories)
                    self.createCalendarCategory(categories)
                calendarUrl = 'https://graph.microsoft.com/v1.0/me/calendars'
                calendarsResponse = requests.get(calendarUrl, headers=newDataHeader)
                if calendarsResponse.status_code == 200:
                    calendars = json.loads(calendarsResponse.content)
                    self.get_calendars(calendars)
                return data
            else:
                data['error'] = 'Something went wrong while fetching token from Office 365.'
                return data

        except Exception as e:
            raise ValidationError('Invalid Credentials!')

    def createPartnerCategory(self, categories):
        for category in categories['value']:
            odooCategory = self.env['res.partner.category'].search(['|', ('categ_id', '=', category['id']), ('name', '=', category['displayName'])])
            if odooCategory:
                odooCategory.write({
                    'categ_id': category['id'],
                    'name': category['displayName'],
                })
            else:
                self.env['res.partner.category'].create({
                    'categ_id': category['id'],
                    'name': category['displayName'],
                })

    def createCalendarCategory(self, categories):
        for category in categories['value']:
            odooCategory = self.env['calendar.event.type'].search(['|', ('categ_id', '=', category['id']), ('name', '=', category['displayName'])])
            if odooCategory:
                odooCategory.write({
                    'categ_id': category['id'],
                    'color': category['color'],
                    'name': category['displayName'],
                })
            else:
                self.env['calendar.event.type'].create({
                    'categ_id': category['id'],
                    'color': category['color'],
                    'name': category['displayName'],
                })

    def get_calendars(self, calendars):
        for calendar in calendars['value']:
            odooCalendar = self.env['office.calendars'].search([('calendar_id', '=', calendar['id'])])
            if odooCalendar:
                odooCalendar.write({
                    'calendar_id': calendar['id'],
                    'name': calendar['name'],
                })
            else:
                self.env['office.calendars'].create({
                    'calendar_id': calendar['id'],
                    'name': calendar['name'],
                })
