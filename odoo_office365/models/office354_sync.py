import logging
import re
from openerp.exceptions import ValidationError, Warning
from openerp.osv import osv
from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
import requests
import json
from datetime import datetime
import time
from datetime import timedelta
import dateutil.parser as p

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/]{3,}=*)([\'"])', re.I)
_import_history = {}


class Office365(models.Model):
    """
    This class give functionality to user for Office365 Integration
    """
    _name = 'office.sync'
    _description = "Office/ Connector"
    # _inherit='res.users'
    res_user = fields.Many2one(model_name="res.users", string="Office365 User Account", compute='compute_user_id',
                               readonly=True)
    code = fields.Char('code', related='res_user.code', readonly=True)
    office365_email = fields.Char('Office365 Email Address', compute='compute_value', readonly=True)
    office365_id_address = fields.Char('Office365 Id Address', compute='compute_value', readonly=True)
    send_mail_flag = fields.Boolean(string='Send messages using office365 Mail', default=True)
    is_active = fields.Boolean('Active Office365 Account')
    is_inbox = fields.Boolean(string="Sync inbox")
    field_name = fields.Char('office365')
    is_sent = fields.Boolean(string="Sync Send")
    event_del_flag = fields.Boolean('Delete events from Office365 calendar when delete in Odoo.',
                                    groups="base.group_user")
    office365_event_del_flag = fields.Boolean('Delete event from Odoo, if the event is deleted from Office 365.',
                                              groups="base.group_user")

    def get_code(self):

        context = dict(self._context)
        settings = self.env['office.settings'].search([])
        if settings.redirect_url and settings.client_id and settings.login_url:
            return {
                'name': 'login',
                'view_id': False,
                "type": "ir.actions.act_url",
                'target': 'self',
                'url': settings.login_url
            }
        else:
            raise ValidationError('Office365 Credentials are missing. Please! ask admin to add Office365 Client id, '
                                  'client secret and redirect Url ')

    def default_user(self):
        return self.env.user.id

    res_user = fields.Many2one('res.users', string='User', default=default_user, readonly=True)
    is_manual_sync = fields.Boolean(string="Custom Date Range", )
    is_auto_sync = fields.Boolean(string="Auto Scheduler", )
    mail_import = fields.Datetime(string="Emails", compute='get_computed_date', required=False, readonly=True)
    calender_import = fields.Datetime(string="Calender", compute='get_computed_date', required=False, readonly=True)
    task_import = fields.Datetime(string="Tasks", compute='get_computed_date', required=False, readonly=True)
    task_export = fields.Datetime(string="Last Export", compute='get_computed_date', required=False, readonly=True)
    calender_export = fields.Datetime(string="Last Export", compute='get_computed_date', required=False, readonly=True)
    contact_export = fields.Datetime(string="Last Export", compute='get_computed_date', required=False, readonly=True)
    contact_import = fields.Datetime(string="Contacts", compute='get_computed_date', required=False, readonly=True)
    is_import_contact = fields.Boolean()
    is_import_email = fields.Boolean()
    is_import_calendar = fields.Boolean()
    is_import_task = fields.Boolean()
    is_export_contact = fields.Boolean()
    is_export_calendar = fields.Boolean()
    is_export_task = fields.Boolean()
    interval_number = fields.Integer(string="Time Interval", required=False, )
    interval_unit = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')
    from_date = fields.Datetime(string="From Date", required=False, )
    to_date = fields.Datetime(string="To Date", required=False, )
    history_line = fields.One2many('sync.history', 'sync_id', copy=True)
    ex_history_line = fields.One2many('export.history', 'sync_export_id', copy=True)
    is_manual_execute = fields.Boolean(string="Manual Execute", )
    categories = fields.Many2many('calendar.event.type', string='Select Event Category')
    contact_categories = fields.Many2many('res.partner.category', string='Select Contact Category')
    calendar_id = fields.Many2one(comodel_name="office.calendars", string="Office365 Calendars", required=False, )
    all_event = fields.Boolean(string="All categories events", )
    for_auto_user_id = fields.Char('User ID')

 
    def insert_history_line(self, added, updated, is_manual, status, action):
        contacts_added = 0
        contacts_updated = 0
        if action == 'contacts':
            contacts_added = added
            contacts_updated = updated
        history = self.env['sync.history']
        history.create({'last_sync': datetime.now(),
                        'no_im_contact': contacts_added,
                        'no_up_contact': contacts_updated,
                        'sync_type': 'manual' if is_manual else 'auto',
                        'sync_id': 1,
                        'no_up_task': 0,
                        'no_im_email': 0,
                        'no_im_calender': 0,
                        'no_up_calender': 0,
                        'no_im_task': 0,
                        'status': status if status else 'Success',

                        })
        self.env.cr.commit()

    def sync_data(self):
        self.env.user.event_del_flag = self.event_del_flag
        self.env.user.office365_event_del_flag = self.office365_event_del_flag
        if self.is_auto_sync:
            if self.interval_unit and self.interval_number:
                activate = self.activate_scheduler()
                self.for_auto_user_id = self._context.get('uid')
                return activate
            else:
                raise Warning('Invalid Interval Time or Interval Unit!')

        if not self.is_auto_sync:
            self.auto_sync_change()

        if self.is_manual_sync:
            if self.is_export_calendar or self.is_import_contact or self.is_import_email or self.is_import_calendar or \
                    self.is_import_task or self.is_export_contact or self.is_export_calendar or self.is_export_task:
                self.is_manual_execute = True
                if self.is_export_calendar:
                    is_manual = True
                    self.export_calendar(is_manual)
                if self.is_import_contact:
                    is_manual = True
                    self.import_contacts(is_manual)
                if self.is_import_email:
                    is_manual = True
                    self.sync_customer_mail(is_manual)
                if self.is_import_calendar:
                    is_manual = True
                    self.import_calendar(is_manual)
                if self.is_import_task:
                    is_manual = True
                    self.import_tasks(is_manual)
                if self.is_export_contact:
                    is_manual = True
                    self.export_contacts(is_manual)
                if self.is_export_task:
                    is_manual = True
                    self.export_tasks(is_manual)
                self.is_manual_execute = False
            else:
                raise Warning("Object not checked!")
        else:
            raise Warning("Auto/Manual sync is turned off.\nPlease select either 'Auto Scheduler' or 'Custom Date Range' to proceed.")

    @api.depends('res_user')
    def get_computed_date(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        if self.res_user:
            self.mail_import = self.res_user.last_mail_import
            self.calender_import = self.res_user.last_calender_import
            self.calender_import = self.res_user.last_calender_import
            self.contact_import = self.res_user.last_contact_import
            self.task_import = self.res_user.last_task_import

    @api.depends('res_user')
    def compute_value(self):
        self.office365_id_address = self.res_user.office365_id_address
        self.office365_email = self.res_user.office365_email

    def get_attachment(self, message):
        context = self._context
        current_uid = context.get('uid')
        if current_uid == None:
            office_connector = self.env['office.sync'].search([])[0]
            no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(no)
        else:
            res_user = self.env['res.users'].sudo().browse(current_uid)
        if res_user.expires_in:
            expires_in = datetime.fromtimestamp(int(res_user.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            nowDateTime = datetime.now()
            if nowDateTime > expires_in:
                self.generate_refresh_token()

        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages/' + message['id'] + '/attachments/',
            headers={
                'Host': 'outlook.office.com',
                'Authorization': 'Bearer {0}'.format(res_user.token),
                'Accept': 'application/json',
                'X-Target-URL': 'http://outlook.office.com',
                'connection': 'keep-Alive'
            }).content
        attachments = json.loads((response.decode('utf-8')))['value']
        attachment_ids = []
        for attachment in attachments:
            _logger.info('Importing attachments of email from office')
            if 'contentBytes' not in attachment or 'name' not in attachment:
                continue
            odoo_attachment = self.env['ir.attachment'].create({
                'datas': attachment['contentBytes'],
                'name': attachment["name"],
                'store_fname': attachment["name"]})
            self.env.cr.commit()
            attachment_ids.append(odoo_attachment.id)
        return attachment_ids

    def get_state_id(self, each_contact, office_home_address, office_state):

        if office_home_address:
            if office_state:
                state = self.env['res.country.state'].search(
                    [('name', '=', office_state)])
                if len(state) > 1:
                    return state[0].id
                elif len(state) == 1:
                    return state[0].id
            else:
                return None
        return None

    def message_wizard(self, context):

        return {
            'name': ('Success'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context

        }


    # Refresh Token

    def refresh_token(self, res_user):
        if res_user.expires_in:
            expires_in = datetime.fromtimestamp(int(res_user.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            now = datetime.now()
            if now > expires_in:
                self.generate_refresh_token()
    def generate_refresh_token(self):
        context = self._context
        current_uid = context.get('uid')
        if current_uid == None:
            office_connector = self.env['office.sync'].search([])[0]
            no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(no)
        else:
            res_user = self.env['res.users'].sudo().browse(current_uid)

        if res_user.refresh_token:
            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings

            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))

            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=refresh_token&refresh_token=' + res_user.refresh_token + '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id + '&client_secret=' + settings.secret
                , headers=header).content

            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_/opt/odoo13/custom_addons/odoo_xerodescription"] = response[
                    "error_description"].replace("\\r\\n", " ")
                raise osv.except_osv(_("Error!"), (_(response["error"] + " " + response["error_description"])))
            else:
                res_user.token = response['access_token']
                res_user.refresh_token = response['refresh_token']
                res_user.expires_in = int(round(time.time() * 1000))
        else:
            _logger.error('Refresh token not found!')

        return response


    # Scheduler

    def activate_scheduler(self):
        done = False
        scheduler_info = []
        while not done:
            try:
                if self.is_export_calendar or self.is_import_contact or self.is_import_email or self.is_import_calendar or \
                        self.is_import_task or self.is_export_contact or self.is_export_calendar or self.is_export_task:

                    if self.is_import_task:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Office365 tasks import')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Office365 tasks import'),
                                                                    ('active', '=', False)])
                        scheduler.user_id = self.env['res.users'].sudo().browse(self._context.get('uid'))   
                        scheduler.active = self.is_import_task
                        scheduler.interval_number = self.interval_number
                        scheduler.interval_type = self.interval_unit
                        self.env.cr.commit()

                    if self.is_export_task:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto office365 tasks export')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto office365 tasks export'),
                                                                    ('active', '=', False)])
                        scheduler.user_id = self.env['res.users'].sudo().browse(self._context.get('uid')) 
                        scheduler.active = self.is_export_task
                        scheduler.interval_number = self.interval_number
                        scheduler.interval_type = self.interval_unit
                        self.env.cr.commit()

                    if self.is_import_contact:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto import Office365 contacts')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto import Office365 contacts'),
                                                                    ('active', '=', False)])
                        scheduler.user_id = self.env['res.users'].sudo().browse(self._context.get('uid')) 
                        scheduler.active = self.is_import_contact
                        scheduler.interval_number = self.interval_number
                        scheduler.interval_type = self.interval_unit
                        self.env.cr.commit()

                    if self.is_export_contact:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto export Office365 contacts')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto export Office365 contacts'),
                                                                    ('active', '=', False)])
                        scheduler.user_id = self.env['res.users'].sudo().browse(self._context.get('uid')) 
                        scheduler.active = self.is_export_contact
                        scheduler.interval_number = self.interval_number
                        scheduler.interval_type = self.interval_unit
                        self.env.cr.commit()


                    if self.is_import_calendar:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto import Office365 Calendar')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto import Office365 Calendar'),
                                                                    ('active', '=', False)])
                        scheduler.user_id = self.env['res.users'].sudo().browse(self._context.get('uid')) 
                        scheduler.active = self.is_import_calendar
                        scheduler.interval_number = self.interval_number
                        scheduler.interval_type = self.interval_unit
                        self.env.cr.commit()

                    if self.is_export_calendar:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto office365 calendar export')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto office365 calendar export'),
                                                                    ('active', '=', False)])
                        scheduler.user_id = self.env['res.users'].sudo().browse(self._context.get('uid')) 
                        scheduler.active = self.is_export_calendar
                        scheduler.interval_number = self.interval_number
                        scheduler.interval_type = self.interval_unit
                        self.env.cr.commit()


                    if self.is_import_email:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Sync Office365 Customers Mail')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Sync Office365 Customers Mail'),
                                                                    ('active', '=', False)])
                        scheduler.user_id = self.env['res.users'].sudo().browse(self._context.get('uid')) 
                        scheduler.active = self.is_import_email
                        scheduler.interval_number = self.interval_number
                        scheduler.interval_type = self.interval_unit
                        self.env.cr.commit()

                else:
                    raise Warning('Please! Select scheduler to activate')
                    self.env.cr.commit()
                done = True
            except Exception as e:
                _logger.error(e)
                print(str(e))

        context = dict(self._context)
        # self.env['office.usersettings'].login_url
        context['message'] = 'Scheduler Successfully Activated! \n The scheduler will execute after {} {}'.format(
            self.interval_number, self.interval_unit)
        return self.message_wizard(context)
    def auto_sync_change(self):
        if not self.is_auto_sync:
            self.is_auto_sync = False
            self.env.cr.commit()
            self.deactivate_auto_sync()
    def deactivate_auto_sync(self):
        done = False
        while not done:
            try:
                if self.is_export_calendar or self.is_import_contact or self.is_import_email or self.is_import_calendar or \
                        self.is_import_task or self.is_export_contact or self.is_export_calendar or self.is_export_task:

                    if self.is_import_task:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Office365 tasks import'),
                                                                ('active', '=', True)])
                        if scheduler:
                            scheduler.active = False
                            self.env.cr.commit()

                    if self.is_export_task:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto office365 tasks export'),
                                                                ('active', '=', True)])
                        if scheduler:
                            scheduler.active = False
                            self.env.cr.commit()

                    if self.is_import_contact:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto import Office365 contacts'),
                                                                ('active', '=', True)])
                        if scheduler:
                            scheduler.active = False
                            self.env.cr.commit()

                    if self.is_export_contact:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto export Office365 contacts'),
                                                                ('active', '=', True)])
                        if scheduler:
                            scheduler.active = False
                            self.env.cr.commit()

                    if self.is_import_calendar:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto import Office365 Calendar'),
                                                                ('active', '=', True)])
                        if scheduler:
                            scheduler.active = False
                            self.env.cr.commit()

                    if self.is_export_calendar:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto office365 calendar export'),
                                                                ('active', '=', True)])
                        if scheduler:
                            scheduler.active = False
                            self.env.cr.commit()

                    if self.is_import_email:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Sync Office365 Customers Mail'),
                                                                ('active', '=', True)])
                        if scheduler:
                            scheduler.active = False
                            self.env.cr.commit()

                self.env.cr.commit()
                done = True
            except Exception as e:
                raise Warning(str(e))


    # Contact & Calendar Categories

    def get_categ_id_contacts(self, contact):
        categ_id = []
        for categ in contact['categories']:
            categ_type_id = self.env['res.partner.category'].search([('name', '=', categ)])
            if categ_type_id:
                categ_type_id.write({'name':categ})
                categ_id.append(categ_type_id[0].id)
            else:
                categ_type_id = categ_type_id.create({'name':categ})
                categ_id.append(categ_type_id[0].id)
        return categ_id
    def get_categ_id(self, event):
        categ_id = []
        for categ in event['categories']:
            categ_type_id = self.env['calendar.event.type'].search([('name', '=', categ)])
            if categ_type_id:
                categ_type_id.write({'name':categ})
                categ_id.append(categ_type_id[0].id)
            else:
                categ_type_id = categ_type_id.create({'name': categ})
                categ_id.append(categ_type_id[0].id)
        return categ_id


    # Calendar

    def getAttendee(self, attendees):
        """
        Get attendees from odoo and convert to attendees Office365 accepting
        :param attendees:
        :return: Office365 accepting attendees

        """
        attendee_list = []
        for attendee in attendees:
            attendee_list.append({
                "status": {
                    "response": 'Accepted',
                    "time": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                },
                "type": "required",
                "emailAddress": {
                    "address": attendee.email,
                    "name": attendee.display_name
                }
            })
        return attendee_list
    def getTime(self, alarm):
        """
        Convert ODOO time to minutes as Office365 accepts time in minutes
        :param alarm:
        :return: time in minutes
        """
        if alarm.interval == 'minutes':
            return alarm[0].duration
        elif alarm.interval == "hours":
            return alarm[0].duration * 60
        elif alarm.interval == "days":
            return alarm[0].duration * 60 * 24
    def getdays(self, meeting):
        """
        Returns days of week the event will occure
        :param meeting:
        :return: list of days
        """
        days = []
        if meeting.weekday == "SU":
            days.append("Sunday")
        if meeting.weekday == "MO":
            days.append("Monday")
        if meeting.weekday == "TU":
            days.append("Tuesday")
        if meeting.weekday == "WE":
            days.append("Wednesday")
        if meeting.weekday == "TH":
            days.append("Thursday")
        if meeting.weekday == "FR":
            days.append("Friday")
        if meeting.weekday == "SA":
            days.append("Saturday")
        return days

    def import_calendar(self, is_manual=None):
        """
        this function imports Office 365  Calendar to Odoo Calendar

        :return:
        """
        office_connector = self.env['office.sync'].search([])[0]

        if not is_manual:
            # no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(self._context.get('uid'))
        else:
            context = self._context
            current_uid = context.get('uid')
            res_user = self.env['res.users'].sudo().browse(current_uid)

        if not res_user.token:
            res_user = self.env['ir.cron'].search([('name', '=', 'Auto import Office365 Calendar')]).user_id

        update_event = 0
        new_event = 0
        status = None
        if res_user.token:
            try:
                self.refresh_token(res_user)
                if self.categories and not self.from_date and not self.to_date:
                    categ_name = []
                    for catg in self.categories:
                        if office_connector.calendar_id and office_connector.calendar_id.calendar_id:
                            url = "https://graph.microsoft.com/v1.0/me/calendars/" + str(
                                office_connector.calendar_id.calendar_id) + "/events?$filter=categories/any(a:a+eq+'{}')".format(
                                catg.name.replace(' ', '+'))
                        else:
                            url = "https://graph.microsoft.com/v1.0/me/events?$filter=categories/any(a:a+eq+'{}')".format(
                                catg.name.replace(' ', '+'))
                        up_event, n_event = self.get_office365_event(url, res_user)
                        update_event = update_event + len(up_event)
                        new_event = new_event + len(n_event)

                elif is_manual and not self.categories:
                    if self.from_date and not self.to_date:
                        raise Warning('Please! Select "To Date" to Import Events.')
                    if self.from_date and self.to_date:
                        if office_connector.calendar_id and office_connector.calendar_id.calendar_id:
                            url = 'https://graph.microsoft.com/v1.0/me/calendars/' + str(
                                office_connector.calendar_id.calendar_id) + '/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}' \
                                      .format(self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                        else:
                            url = 'https://graph.microsoft.com/v1.0/me/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}' \
                                .format(self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                        self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    else:
                        if office_connector.calendar_id and office_connector.calendar_id.calendar_id:
                            url = 'https://graph.microsoft.com/v1.0/me/calendars/' + str(
                                office_connector.calendar_id.calendar_id) + '/events'

                        else:
                            url = 'https://graph.microsoft.com/v1.0/me/events'

                elif self.categories and self.from_date and self.to_date:
                    categ_name = []
                    for catg in self.categories:
                        if self.from_date and not self.to_date:
                            raise Warning('Please! Select "To Date" to Import Events.')
                        if self.from_date and self.to_date:
                            if office_connector.calendar_id and office_connector.calendar_id.calendar_id:
                                url = "https://graph.microsoft.com/v1.0/me/calendars/" + str(
                                    office_connector.calendar_id.calendar_id) + "/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}".format(
                                    self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"), self.to_date.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ")) + " and categories/any(a:a+eq+'{}')".format(
                                    catg.name.replace(' ', '+'))
                            else:
                                url = "https://graph.microsoft.com/v1.0/me/calendars/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}".format(
                                    self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"), self.to_date.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ")) + " and categories/any(a:a+eq+'{}')".format(
                                    catg.name.replace(' ', '+'))

                            up_event, n_event = self.get_office365_event(url, res_user)
                            update_event = update_event + len(up_event)
                            new_event = new_event + len(n_event)

                else:
                    custom_data = self.env['office.sync'].search([])[0]
                    if custom_data.from_date and custom_data.to_date:
                        if office_connector.calendar_id and office_connector.calendar_id.calendar_id:
                            url = 'https://graph.microsoft.com/v1.0/me/calendars/' + str(
                                office_connector.calendar_id.calendar_id) + '/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}' \
                                      .format(custom_data.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              custom_data.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                        else:
                            url = 'https://graph.microsoft.com/v1.0/me/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}' \
                                .format(custom_data.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                        custom_data.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))

                    else:
                        if office_connector.calendar_id and office_connector.calendar_id.calendar_id:
                            url = 'https://graph.microsoft.com/v1.0/me/calendars/' + str(
                                office_connector.calendar_id.calendar_id) + '/events'
                        else:
                            url = 'https://graph.microsoft.com/v1.0/me/events'

                up_event, n_event = self.get_office365_event(url, res_user)
                update_event = update_event + len(up_event)
                new_event = new_event + len(n_event)

            except Exception as e:
                status = 'Error'
                if is_manual:
                    _logger.error(e)
                    raise Warning(e)
                _logger.error(e)

            finally:
                # res_user.last_calender_import = datetime.now()
                type = None
                if not is_manual:
                    type = 'auto'
                else:
                    type = 'manual'
                history = self.env['sync.history']
                history.create({'last_sync': datetime.now(),
                                'no_im_calender': new_event if new_event else 0,
                                'no_up_calender': update_event if update_event else 0,
                                'sync_type': type,
                                'no_up_task': 0,
                                'no_up_contact': 0,
                                'no_im_contact': 0,
                                'no_im_email': 0,
                                'no_im_task': 0,
                                'sync_id': 1,
                                'status': status if status else 'Success'
                                })

                self.env.cr.commit()

        else:
            raise Warning("Token not found! Please Go to user preference from left corner and login Office365 Account ")
    def get_office365_event(self, url, res_user, categ_name=None):
        update_event = []
        new_event = []
        office_connector = self.env['office.sync'].search([])[0]
        if office_connector.calendar_id:
            odoo_event = self.env['calendar.event'].search(
                [('office_id', '!=', None), ('calendar_id', '=', office_connector.calendar_id.id)])
        else:
            odoo_event = self.env['calendar.event'].search([('office_id', '!=', None)])
        odoo_event_ids = odoo_event.mapped('office_id')

        new_url = url

        try:
            while True:
                url = new_url
                response = requests.get(
                    url,
                    headers={
                        'Authorization': 'Bearer {0}'.format(res_user.token),
                        'Accept': 'application/json',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(response)
                    _logger.error('Office365:{}'.format(json.loads((response.decode('utf-8')))))
                events = json.loads((response.decode('utf-8')))['value']
                for event in events:
                    if event['id'] in odoo_event_ids and res_user.office365_event_del_flag:
                        odoo_event_ids.remove(event['id'])
                    if not event['subject'] and event['body']:
                        continue
                    _logger.info('Office365: Getting event {} from Office365'.format(event['id']))

                    # if 'showAs' in event:
                    odoo_meeting = self.env['calendar.event'].search([("office_id", "=", event['id'])])
                    categ_id = None
                    if 'categories' in event and event['categories']:
                        categ_id = self.get_categ_id(event)
                    if odoo_meeting:
                        odoo_meeting = self.env['calendar.event'].search([("office_id", "=", event['id'])])[0]
                        office_modification_date = datetime.strptime(
                            datetime.strftime(p.parse(event['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                            "%Y-%m-%dT%H:%M:%S")
                        if office_modification_date != odoo_meeting.modified_date:
                            if odoo_meeting.modified_date:
                                if office_modification_date < odoo_meeting.modified_date or \
                                        office_modification_date == odoo_meeting.modified_date:
                                    continue
                            _logger.info('Office365: Updating event {} In Odoo'.format(event['id']))

                            rule_type = None
                            if event['recurrence']:
                                if 'absolute' in event['recurrence']['pattern']['type']:
                                    rule_type = event['recurrence']['pattern']['type'].replace('absolute', '').lower()
                                elif 'relative' in event['recurrence']['pattern']['type']:
                                    rule_type = event['recurrence']['pattern']['type'].replace('relative', '').lower()
                                else:
                                    rule_type = event['recurrence']['pattern']['type']

                            else:
                                rule_type = None

                            final_date = None
                            if event['recurrence']:
                                if event['recurrence']['range']['type'] == 'noEnd':
                                    final_date = datetime.strptime(event['recurrence']['range']['startDate'],
                                                                   '%Y-%m-%d').strftime('%Y-%m-%d')
                                else:
                                    final_date = datetime.strptime(event['recurrence']['range']['endDate'],
                                                                   '%Y-%m-%d').strftime('%Y-%m-%d')

                            else:
                                final_date = None

                            day_date_selection = None
                            index = None
                            week_day = None
                            day = None

                            if event['recurrence']:
                                if rule_type == 'monthly':

                                    day = 0

                                    if event['recurrence']['pattern']['dayOfMonth'] == 0:
                                        day_date_selection = 'day'
                                        if event['recurrence']['pattern']['index'] == 'first':
                                            index = '1'
                                        elif event['recurrence']['pattern']['index'] == 'second':
                                            index = '2'
                                        elif event['recurrence']['pattern']['index'] == 'third':
                                            index = '3'
                                        elif event['recurrence']['pattern']['index'] == 'fourth':
                                            index = '4'
                                        elif event['recurrence']['pattern']['index'] == 'fifth':
                                            index = '5'
                                        elif event['recurrence']['pattern']['index'] == 'last':
                                            index = '-1'

                                        if event['recurrence']['pattern']['daysOfWeek'][0] == 'monday':
                                            week_day = 'MO'
                                        elif event['recurrence']['pattern']['daysOfWeek'][0] == 'tuesday':
                                            week_day = 'TU'
                                        elif event['recurrence']['pattern']['daysOfWeek'][0] == 'wednesday':
                                            week_day = 'WE'
                                        elif event['recurrence']['pattern']['daysOfWeek'][0] == 'thursday':
                                            week_day = 'TH'
                                        elif event['recurrence']['pattern']['daysOfWeek'][0] == 'friday':
                                            week_day = 'FR'
                                        elif event['recurrence']['pattern']['daysOfWeek'][0] == 'saturday':
                                            week_day = 'SA'
                                        elif event['recurrence']['pattern']['daysOfWeek'][0] == 'sunday':
                                            week_day = 'SU'
                                        else:
                                            week_day = None

                                else:
                                    day_date_selection = 'date'
                                    day = event['recurrence']['pattern']['dayOfMonth']

                            else:
                                day_date_selection = None
                                index = None
                                week_day = None
                                day = None

                            partner_ids = []
                            attendee_ids = []
                            for attendee in event['attendees']:
                                if 'address' in attendee['emailAddress']:
                                    partner = self.env['res.partner'].search(
                                        [('email', "=", attendee['emailAddress']['address'])])
                                    if not partner:
                                        _logger.info('Office365: Creating attendee {} In Odoo'.format(
                                            attendee['emailAddress']['address']))
                                        partner = self.env['res.partner'].create({
                                            'name': attendee['emailAddress']['name'],
                                            'email': attendee['emailAddress']['address'],
                                            'location': 'Office365 Attendee',
                                        })
                                    partner_ids.append(partner[0].id)
                                    _logger.info(
                                        'Office365: Creating attendee {} In Odoo'.format(
                                            attendee['emailAddress']['address']))

                                if not event['attendees']:
                                    partner_ids.append(res_user.partner_id.id)
                            
                            odoo_meeting.write({
                                'is_update': False,
                                'calendar_id': office_connector.calendar_id.id if office_connector.calendar_id else None,
                                'office_id': event['id'],
                                'name': event['subject'],
                                'category_name': event['categories'][0] if 'categories' in event and event[
                                    'categories'] else None,
                                "description": event['bodyPreview'],
                                'location': (event['location']['address']['city'] + ', ' + event['location']['address'][
                                    'countryOrRegion']) if 'address' in event['location'] and 'city' in
                                                           event['location'][
                                                               'address'].keys() else "",
                                'start': datetime.strptime(
                                    datetime.strftime(p.parse(event['start']['dateTime']), "%Y-%m-%dT%H:%M:%S"),
                                    "%Y-%m-%dT%H:%M:%S"),
                                'stop': datetime.strptime(
                                    datetime.strftime(p.parse(event['end']['dateTime']), "%Y-%m-%dT%H:%M:%S"),
                                    "%Y-%m-%dT%H:%M:%S"),
                                'allday': event['isAllDay'],
                                'categ_ids': [(6, 0, categ_id)] if categ_id else None,
                                'show_as': event['showAs'] if 'showAs' in event and (
                                        event['showAs'] == 'free' or event['showAs'] == 'busy') else None,
                                'recurrency': True if event['recurrence'] else False,
                                'end_type': 'end_date' if event['recurrence'] else "",
                                'rrule_type': rule_type,
                                'count': event['recurrence']['range']['numberOfOccurrences'] if event[
                                    'recurrence'] else "",
                                'until': final_date,
                                'mo': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                    'pattern'].keys() and 'monday' in event['recurrence']['pattern'][
                                                  'daysOfWeek'] else False,
                                'tu': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                    'pattern'].keys() and 'tuesday' in event['recurrence']['pattern'][
                                                  'daysOfWeek'] else False,
                                'we': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                    'pattern'].keys() and 'wednesday' in event['recurrence']['pattern'][
                                                  'daysOfWeek'] else False,
                                'th': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                    'pattern'].keys() and 'thursday' in event['recurrence']['pattern'][
                                                  'daysOfWeek'] else False,
                                'fr': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                    'pattern'].keys() and 'friday' in event['recurrence']['pattern'][
                                                  'daysOfWeek'] else False,
                                'sa': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                    'pattern'].keys() and 'saturday' in event['recurrence']['pattern'][
                                                  'daysOfWeek'] else False,
                                'su': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                    'pattern'].keys() and 'sunday' in event['recurrence']['pattern'][
                                                  'daysOfWeek'] else False,
                                'month_by': day_date_selection,
                                'day': day,
                                'byday': index,
                                'weekday': week_day,
                                'modified_date': datetime.strptime(
                                    datetime.strftime(p.parse(event['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                                    "%Y-%m-%dT%H:%M:%S"),
                                'partner_ids': [[6, 0, partner_ids]] if len(partner_ids) > 0 else None
                            })
                            self.env.cr.commit()
                            update_event.append(odoo_meeting.id)

                    else:
                        _logger.info('Office365: Creating event {} In Odoo'.format(event['id']))

                        rule_type = None
                        if event['recurrence']:
                            if 'absolute' in event['recurrence']['pattern']['type']:
                                rule_type = event['recurrence']['pattern']['type'].replace('absolute', '').lower()
                            elif 'relative' in event['recurrence']['pattern']['type']:
                                rule_type = event['recurrence']['pattern']['type'].replace('relative', '').lower()
                            else:
                                rule_type = event['recurrence']['pattern']['type']
                        else:
                            rule_type = None

                        final_date = None
                        if event['recurrence']:
                            if event['recurrence']['range']['type'] == 'noEnd':
                                final_date = datetime.strptime(event['recurrence']['range']['startDate'],
                                                               '%Y-%m-%d').strftime('%Y-%m-%d')
                            else:
                                final_date = datetime.strptime(event['recurrence']['range']['endDate'],
                                                               '%Y-%m-%d').strftime('%Y-%m-%d')
                        else:
                            final_date = None

                        day_date_selection = None
                        index = None
                        week_day = None
                        day = None

                        if event['recurrence']:
                            if rule_type == 'monthly':

                                day = 0

                                if event['recurrence']['pattern']['dayOfMonth'] == 0:
                                    day_date_selection = 'day'
                                    if event['recurrence']['pattern']['index'] == 'first':
                                        index = '1'
                                    elif event['recurrence']['pattern']['index'] == 'second':
                                        index = '2'
                                    elif event['recurrence']['pattern']['index'] == 'third':
                                        index = '3'
                                    elif event['recurrence']['pattern']['index'] == 'fourth':
                                        index = '4'
                                    elif event['recurrence']['pattern']['index'] == 'fifth':
                                        index = '5'
                                    elif event['recurrence']['pattern']['index'] == 'last':
                                        index = '-1'

                                    if event['recurrence']['pattern']['daysOfWeek'][0] == 'monday':
                                        week_day = 'MO'
                                    elif event['recurrence']['pattern']['daysOfWeek'][0] == 'tuesday':
                                        week_day = 'TU'
                                    elif event['recurrence']['pattern']['daysOfWeek'][0] == 'wednesday':
                                        week_day = 'WE'
                                    elif event['recurrence']['pattern']['daysOfWeek'][0] == 'thursday':
                                        week_day = 'TH'
                                    elif event['recurrence']['pattern']['daysOfWeek'][0] == 'friday':
                                        week_day = 'FR'
                                    elif event['recurrence']['pattern']['daysOfWeek'][0] == 'saturday':
                                        week_day = 'SA'
                                    elif event['recurrence']['pattern']['daysOfWeek'][0] == 'sunday':
                                        week_day = 'SU'
                                    else:
                                        week_day = None

                            else:
                                day_date_selection = 'date'
                                day = event['recurrence']['pattern']['dayOfMonth']

                        else:
                            day_date_selection = None
                            index = None
                            week_day = None
                            day = None

                        
                        
                        partner_ids = []
                        attendee_ids = []
                        for attendee in event['attendees']:
                            if 'address' in attendee['emailAddress']:
                                partner = self.env['res.partner'].search(
                                    [('email', "=", attendee['emailAddress']['address'])])
                                if not partner:
                                    _logger.info('Office365: Creating attendee {} In Odoo'.format(
                                        attendee['emailAddress']['address']))
                                    partner = self.env['res.partner'].create({
                                        'name': attendee['emailAddress']['name'],
                                        'email': attendee['emailAddress']['address'],
                                        'location': 'Office365 Attendee',
                                    })
                                partner_ids.append(partner[0].id)
                                _logger.info(
                                    'Office365: Creating attendee {} In Odoo'.format(
                                        attendee['emailAddress']['address']))

                            if not event['attendees']:
                                partner_ids.append(res_user.partner_id.id)
          
                        odoo_event = self.env['calendar.event'].create({
                            'office_id': event['id'],
                            'is_update': False,
                            'name': event['subject'],
                            'calendar_id': office_connector.calendar_id.id if office_connector.calendar_id else None,
                            'category_name': event['categories'][0] if 'categories' in event and event[
                                'categories'] else None,
                            "description": event['bodyPreview'],
                            'location': (event['location']['address']['city'] + ', ' + event['location']['address'][
                                'countryOrRegion']) if 'address' in event['location'] and 'city' in
                                                       event['location'][
                                                           'address'].keys() else "",
                            'start': datetime.strptime(
                                datetime.strftime(p.parse(event['start']['dateTime']), "%Y-%m-%dT%H:%M:%S"),
                                "%Y-%m-%dT%H:%M:%S"),
                            'stop': datetime.strptime(
                                datetime.strftime(p.parse(event['end']['dateTime']), "%Y-%m-%dT%H:%M:%S"),
                                "%Y-%m-%dT%H:%M:%S"),
                            'allday': event['isAllDay'],

                            'categ_ids': [[6, 0, categ_id]] if categ_id else None,
                            'show_as': event['showAs'] if 'showAs' in event and (
                                    event['showAs'] == 'free' or event['showAs'] == 'busy') else None,
                            'recurrency': True if event['recurrence'] else False,
                            'end_type': 'end_date' if event['recurrence'] else "",
                            'rrule_type': rule_type,
                            'count': event['recurrence']['range']['numberOfOccurrences'] if event[
                                'recurrence'] else "",
                            'until': final_date,
                            'mo': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'monday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'tu': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'tuesday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'we': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'wednesday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'th': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'thursday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'fr': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'friday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'sa': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'saturday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'su': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'sunday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'month_by': day_date_selection,
                            'day': day,
                            'byday': index,
                            'weekday': week_day,
                            'modified_date': datetime.strptime(
                                datetime.strftime(p.parse(event['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                                "%Y-%m-%dT%H:%M:%S"),
                            'partner_ids': [[6, 0, partner_ids]] if len(partner_ids) > 0 else None
                        })
                        self.env.cr.commit()
                        new_event.append(odoo_event.id)


                if odoo_event_ids and res_user.office365_event_del_flag:
                    delete_event = self.env['calendar.event'].search([('office_id', 'in', odoo_event_ids)])
                    delete_event.unlink()

                response = json.loads((response.decode('utf-8')))

                if '@odata.nextLink' in response:
                    new_url = response['@odata.nextLink']
                else:
                    return update_event, new_event
                    break



        # res_user.last_calender_import = datetime.now()

        except Exception as e:
            raise Warning(e)
    def export_calendar(self, is_manual=None):
        """
        this function export  odoo calendar event  to office 365 Calendar

        """
        office_connector = self.env['office.sync'].search([])[0]
        if not is_manual:
            # no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(self._context.get('uid'))
        else:
            context = self._context
            current_uid = context.get('uid')
            res_user = self.env['res.users'].sudo().browse(current_uid)

        if not res_user.token:
            res_user = self.env['ir.cron'].search([('name', '=', 'Auto office365 calendar export')]).user_id

        export_event = []
        update_event = []
        status = None
        from_date = None
        to_date = None
        if res_user.token:
            try:
                self.refresh_token(res_user)
                if is_manual:
                    if self.from_date and not self.to_date:
                        raise Warning('Please! Select "To Date" to Import Events.')
                    if self.from_date and self.to_date:
                        from_date = self.from_date
                        to_date = self.to_date
                    else:
                        if res_user.last_calender_import:
                            from_date = res_user.last_calender_import
                            to_date = datetime.now()

                else:
                    custom_data = self.env['office.sync'].search([])[0]
                    if custom_data.from_date and custom_data.to_date:
                        from_date = custom_data.from_date
                        to_date = custom_data.to_date
                    elif res_user.last_contact_import:
                        from_date = res_user.last_contact_import
                        to_date = datetime.now()

                header = {
                    'Authorization': 'Bearer {0}'.format(res_user.token),
                    'Content-Type': 'application/json'
                }
                if office_connector.calendar_id and office_connector.calendar_id.calendar_id:
                    calendar_id = office_connector.calendar_id.calendar_id
                else:
                    response = requests.get(
                        'https://graph.microsoft.com/v1.0/me/calendars',
                        headers={
                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(res_user.token),
                            'Accept': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        }).content
                    res_data = json.loads((response.decode('utf-8')))
                    if 'value' not in res_data.keys():
                        raise osv.except_osv(("Access Token Expired!"), (" Please Regenerate Access Token !"))
                    calendars = res_data['value']
                    calendar_id = calendars[0]['id']

                meetings = self.env['calendar.event'].search([("create_uid", '=', res_user.id)])
                if from_date and to_date:
                    meetings = meetings.search([('write_date', '>=', from_date), ('write_date', '<=', to_date)])

                added = []
                for meeting in meetings:
                    temp = meeting
                    id = str(meeting.id).split('-')[0]
                    metngs = [meeting for meeting in meetings if id in str(meeting.id)]
                    index = len(metngs)
                    categ_name = []
                    if meeting.categ_ids:
                        for cat in meeting.categ_ids:
                            categ_name.append(cat.name)
                    # meeting = metngs[index - 1]

                    if meeting.start and type(meeting.start) is datetime:
                        metting_start = meeting.start.strftime('%Y-%m-%d T %H:%M:%S')
                    else:
                        metting_start = meeting.start

                    if meeting.stop and type(meeting.stop) is datetime:
                        metting_stop = meeting.stop.strftime('%Y-%m-%d T %H:%M:%S')
                    else:
                        metting_stop = meeting.stop

                    payload = {
                        "subject": meeting.name,
                        "categories": categ_name,
                        "attendees": self.getAttendee(meeting.attendee_ids),
                        'reminderMinutesBeforeStart': self.getTime(meeting.alarm_ids),
                        "start": {
                            "dateTime": metting_start,
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": metting_stop,
                            "timeZone": "UTC"
                        },
                        "showAs": meeting.show_as,
                        "location": {
                            "displayName": meeting.location if meeting.location else "",
                        },

                    }
                    if meeting.recurrency:

                        # Added dummy data to initialise variables

                        daysOfWeek = "Monday"
                        event_type = "absoluteMonthly"
                        week_index = "first"
                        day = 0

                        if meeting.month_by == 'date':
                            daysOfWeek = self.getdays(meeting)
                            event_type = 'absoluteMonthly'
                            week_index = "first"
                            day = meeting.start.day

                        elif meeting.month_by == 'day':
                            daysOfWeek = self.getdays(meeting)
                            event_type = 'relativeMonthly'
                            day = meeting.start.day
                            if meeting.byday == '1':
                                week_index = 'first'
                            elif meeting.byday == '2':
                                week_index = 'second'
                            elif meeting.byday == '3':
                                week_index = 'third'
                            elif meeting.byday == '4':
                                week_index = 'fourth'
                            elif meeting.byday == '-1':
                                week_index = 'last'

                        else:
                            event_type = ('Absolute' if meeting.rrule_type != "weekly" and meeting.rrule_type != "daily" else "") + meeting.rrule_type
                            daysOfWeek = "Monday"
                            week_index = "first"
                            day = meeting.start.day

                        payload.update({"recurrence": {
                            "pattern": {
                                "daysOfWeek": self.getdays(meeting),
                                "type": event_type,
                                "interval": meeting.interval,
                                "month": meeting.start.month,
                                "dayOfMonth": day,
                                "firstDayOfWeek": "sunday",
                                "index": week_index,
                            },
                            "range": {
                                "type": "endDate",
                                "startDate": str(meeting.start).split(" ")[0],
                                "endDate": str(meeting.until),
                                "recurrenceTimeZone": "UTC",
                                "numberOfOccurrences": meeting.count,
                            }
                        }})
                    if meeting.name not in added:
                        if not meeting.office_id:
                            response = requests.post(
                                'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events',
                                headers=header, data=json.dumps(payload)).content
                            if 'id' in json.loads((response.decode('utf-8'))):
                                temp.write({
                                    'office_id': json.loads((response.decode('utf-8')))['id']
                                })
                                temp.is_update = False
                                self.env.cr.commit()
                                export_event.append(json.loads((response.decode('utf-8')))['id'])
                                if meeting.recurrency:
                                    added.append(meeting.name)

                        elif meeting.is_update:
                            url = "https://graph.microsoft.com/v1.0/me/events/{}".format(meeting.office_id)
                            response = requests.get(
                                url,
                                headers={
                                    'Host': 'outlook.office.com',
                                    'Authorization': 'Bearer {0}'.format(res_user.token),
                                    'Accept': 'application/json',
                                    'X-Target-URL': 'http://outlook.office.com',
                                    'connection': 'keep-Alive'
                                }).content
                            res_event = json.loads((response.decode('utf-8')))
                            if 'id' not in res_event.keys():
                                raise osv.except_osv(("Access Token Expired!"), (" Please Regenerate Access Token !"))
                            modified_at = datetime.strptime(
                                res_event['lastModifiedDateTime'].split(".")[0], '%Y-%m-%dT%H:%M:%S'
                            )

                            if modified_at != meeting.modified_date:
                                if meeting.modified_date:
                                    if modified_at > meeting.modified_date or modified_at == meeting.modified_date:
                                        continue

                            response = requests.patch(
                                'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events/' + meeting.office_id,
                                headers=header, data=json.dumps(payload)).content
                            if 'id' in json.loads((response.decode('utf-8'))):
                                temp.write({
                                    'office_id': json.loads((response.decode('utf-8')))['id']
                                })
                                update_event.append(json.loads((response.decode('utf-8')))['id'])
                                meeting.is_update = False
                                self.env.cr.commit()
                                if meeting.recurrency:
                                    added.append(meeting.name)

            except Exception as e:
                _logger.error(e)
                raise ValidationError(_(str(e)))

            finally:
                # self.ex_auto_calender = False
                typee = None
                if not is_manual:
                    typee = 'auto'
                else:
                    typee = 'manual'
                history = self.env['export.history']
                history.create({'last_sync': datetime.now(),
                                'no_ex_calender': len(export_event) if export_event else 0,
                                'no_up_calender': len(update_event) if update_event else 0,
                                'sync_type': typee,
                                'no_up_task': 0,
                                'no_up_contact': 0,
                                'no_ex_contact': 0,
                                'no_ex_email': 0,
                                'no_ex_task': 0,
                                'sync_export_id': 1,
                                'status': status if status else 'Success'
                                })

                self.env.cr.commit()
        else:
            raise Warning("Token not found! Please Go to user preference from left corner and login Office365 Account ")
 
    @api.model
    def auto_import_calendar(self):
        _logger.info('Calender Scheduler Import: Activated ')
        self.import_calendar(is_manual=False)
        _logger.info('Calender Scheduler: Successfully import event from office365')
    @api.model
    def auto_export_calendar(self):
        _logger.info('Calender Scheduler Export: Activated')
        self.export_calendar(is_manual=False)
        _logger.info('Calender Scheduler: Successfully export event to office365')


    # Tasks

    def import_tasks(self, is_manual=None):

        """
        import task from office 365 to odoo

        :return: None
        """
        office_connector = self.env['office.sync'].search([])[0]

        if not is_manual:
            # no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(self._context.get('uid'))
        else:
            context = self._context
            current_uid = context.get('uid')
            res_user = self.env['res.users'].sudo().browse(current_uid)


        if not res_user.token:
            res_user = self.env['ir.cron'].search([('name', '=', 'Auto Office365 tasks import')]).user_id

        new_task = []
        update_task = []
        status = None
        if res_user.token:
            try:
                self.refresh_token(res_user)

                url = 'https://graph.microsoft.com/v1.0/me/todo/lists/tasks'

                response = requests.get(
                        url,
                        headers={
                            'Authorization': 'Bearer {0}'.format(res_user.token),
                            'Content-type': 'application/json',
                            'connection': 'keep-Alive'
                        }).content
                res_data = json.loads((response.decode('utf-8')))

                new_url = 'https://graph.microsoft.com/v1.0/me/todo/lists/' + res_data['id'] + '/tasks'





                if is_manual:
                    #
                    if self.from_date and not self.to_date:
                        raise Warning('Please! Select "To Date" to Import Events.')
                    if self.from_date and self.to_date:
                        url = new_url + \
                             '?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}' \
                            .format(self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    else:
                        url = new_url

                else:
                    custom_data = self.env['office.sync'].search([])[0]
                    if custom_data.from_date and custom_data.to_date:
                        url = new_url + \
                              '?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}' \
                            .format(custom_data.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    custom_data.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))

                    elif res_user.last_calender_import:
                        url = new_url + \
                              '?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}' \
                            .format(res_user.last_calender_import.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
                    else:
                        url = new_url

                while True:
                    response = requests.get(
                        url,
                        headers={
                            'Authorization': 'Bearer {0}'.format(res_user.token),
                            'Content-type': 'application/json',
                            'connection': 'keep-Alive'
                        }).content
                    res_data = json.loads((response.decode('utf-8')))
                    if 'value' not in res_data.keys():
                        raise osv.except_osv(response)
                    tasks = res_data['value']
                    partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')])
                    partner = self.env['res.partner'].search([('email', '=', res_user.email)])
                    activity_type = self.env['mail.activity.type'].search([('name', '=', 'Todo')])
                    if partner_model:
                        res_user.is_task_sync_on = True
                        self.env.cr.commit()
                        for task in tasks:
                            odoo_task = self.env['mail.activity'].search([('office_id', '=', task['id'])])
                            if not odoo_task and task['status'] != 'completed':
                                if 'dueDateTime' in task:
                                    if task['dueDateTime'] is None:
                                        continue
                                else:
                                    continue

                                self.env['mail.activity'].create({
                                    'res_id': partner[0].id,
                                    'activity_type_id': activity_type.id,
                                    'summary': task['title'],
                                    'date_deadline': (
                                        datetime.strptime(task['dueDateTime']['dateTime'][:-16], '%Y-%m-%dT')).strftime(
                                        '%Y-%m-%d'),
                                    'note': task['body']['content'],
                                    'res_model_id': partner_model.id,
                                    'office_id': task['id'],
                                    'modified_date': datetime.strptime(datetime.strftime(p.parse(
                                            task['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                                            "%Y-%m-%dT%H:%M:%S"),
                                })
                                new_task.append(task['id'])
                            elif odoo_task and task['status'] != 'completed':
                                modified_at = datetime.strptime(
                                    task['lastModifiedDateTime'].split(".")[0], '%Y-%m-%dT%H:%M:%S'
                                )
                                if modified_at != odoo_task.modified_date:
                                    if odoo_task.modified_date:
                                        if modified_at < odoo_task.modified_date or modified_at == odoo_task.modified_date:
                                            continue
                                    odoo_task.write({
                                        'res_id': partner[0].id,
                                        'activity_type_id': activity_type.id,
                                        'summary': task['title'],
                                        'date_deadline': (
                                            datetime.strptime(task['dueDateTime']['dateTime'][:-16],
                                                              '%Y-%m-%dT')).strftime(
                                            '%Y-%m-%d'),
                                        'note': task['body']['content'],
                                        'res_model_id': partner_model.id,
                                        'office_id': task['id'],
                                        'modified_date': datetime.strptime(datetime.strftime(p.parse(
                                                task['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                                                "%Y-%m-%dT%H:%M:%S"),
                                    })
                                    update_task.append(odoo_task.id)
                                    self.env.cr.commit()
                            elif odoo_task and task['status'] == 'completed':
                                odoo_task.unlink()
                            self.env.cr.commit()

                    response = json.loads((response.decode('utf-8')))

                    if '@odata.nextLink' in response:
                        url = response['@odata.nextLink']
                    else:
                        break

                res_user.last_task_import = datetime.now()

            except Exception as e:
                status = 'Error'
                _logger.error(e)
                res_user.is_task_sync_on = False
                self.env.cr.commit()
                raise ValidationError(_(str(e)))

            finally:
                history = self.env['sync.history']
                history.create({'last_sync': datetime.now(),
                                'no_im_task': len(new_task) if new_task else 0,
                                'no_up_task': len(update_task) if update_task else 0,
                                'sync_type': 'manual' if is_manual else 'auto',
                                'no_up_calender': 0,
                                'no_up_contact': 0,
                                'no_im_contact': 0,
                                'no_im_email': 0,
                                'no_im_calender': 0,
                                'status': status if status else 'Success',
                                'sync_id': 1,
                                })

                self.env.cr.commit()
        else:
            raise Warning("Token not found! Please Go to user preference from left corner and login Office365 Account ")
    def export_tasks(self, is_manual=None):

        office_connector = self.env['office.sync'].search([])[0]

        if not is_manual:
            # no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(self._context.get('uid'))
        else:
            context = self._context
            current_uid = context.get('uid')
            res_user = self.env['res.users'].sudo().browse(current_uid)

        if not res_user.token:
            res_user = self.env['ir.cron'].search([('name', '=', 'Auto office365 tasks export')]).user_id

        export_task = []
        update_task = []
        status = None
        from_date = None
        to_date = None
        if res_user.token:
            try:
                self.refresh_token(res_user)
                if is_manual:
                    if self.from_date and not self.to_date:
                        raise Warning('Please! Select "To Date" to Import Events.')
                    if self.from_date and self.to_date:
                        from_date = self.from_date
                        to_date = self.to_date
                    else:
                        if res_user.last_calender_import:
                            from_date = res_user.last_calender_import
                            to_date = datetime.now()

                else:
                    custom_data = self.env['office.sync'].search([])[0]
                    if custom_data.from_date and custom_data.to_date:
                        from_date = custom_data.from_date
                        to_date = custom_data.to_date
                    elif res_user.last_contact_import:
                        from_date = res_user.last_contact_import
                        to_date = datetime.now()

                odoo_activities = self.env['mail.activity'].search([('res_id', '=', res_user.partner_id.id)]).sudo()
                if from_date and to_date:
                    odoo_activities = odoo_activities.search(
                        [('write_date', '>=', from_date), ('write_date', '<=', to_date)])



                url = 'https://graph.microsoft.com/v1.0/me/todo/lists/tasks'

                response = requests.get(
                        url,
                        headers={
                            'Authorization': 'Bearer {0}'.format(res_user.token),
                            'Content-type': 'application/json',
                            'connection': 'keep-Alive'
                        }).content
                res_data = json.loads((response.decode('utf-8')))

                new_url = 'https://graph.microsoft.com/v1.0/me/todo/lists/' + res_data['id'] + '/tasks'

                for activity in odoo_activities:
                    url = new_url
                    if activity.office_id:
                        # url += '/' + activity.office_id
                        url = url

                    data = {
                        'title': activity.summary if activity.summary else activity.display_name,
                        "body": {
                            "contentType": "html",
                            "content": activity.note if activity.note else ""
                        },
                        "dueDateTime": {
                            "dateTime": str(activity.date_deadline) + 'T00:00:00Z',
                            "timeZone": "UTC"
                        },
                    }
                    if activity.office_id:
                        if activity.is_update:
                            url = new_url + '/{}'.format(activity.office_id)
                            response = requests.get(
                                url,
                                headers={
                                    'Authorization': 'Bearer {0}'.format(res_user.token),
                                    'Content-type': 'application/json',
                                    'connection': 'keep-Alive'
                                }).content
                            res_task = json.loads((response.decode('utf-8')))
                            if 'id' not in res_task.keys():
                                raise osv.except_osv(
                                    ("Access Token Expired!"),
                                    (" Please Regenerate Access Token !")
                                )
                            modified_at = datetime.strptime(
                                res_task['lastModifiedDateTime'].split(".")[0], '%Y-%m-%dT%H:%M:%S'
                            )
                            if modified_at != activity.modified_date:
                                if activity.modified_date:
                                    if modified_at > activity.modified_date or modified_at == activity.modified_date:
                                        continue
                            response = requests.patch(
                                url, data=json.dumps(data),
                                headers={
                                    'Authorization': 'Bearer {0}'.format(res_user.token),
                                    'Content-type': 'application/json',
                                    'connection': 'keep-Alive'
                                }).content
                            update_task.append(activity.office_id)
                            activity.is_update = False
                    else:

                        response = requests.post(
                            url, data=json.dumps(data),
                            headers={
                                'Authorization': 'Bearer {0}'.format(res_user.token),
                                'Content-type': 'application/json',
                                'connection': 'keep-Alive'
                            }).content

                        if 'id' not in json.loads((response.decode('utf-8'))).keys():
                            raise osv.except_osv(_("Error!"), (_(response["error"])))
                        activity.office_id = json.loads((response.decode('utf-8')))['id']
                        export_task.append(activity.office_id)
                        activity.is_update = False
                    self.env.cr.commit()
            except Exception as e:
                status = 'Error'
                if is_manual:
                    raise Warning(e)
                    _logger.error(e)
                else:
                    _logger.error(e)
            finally:
                history = self.env['export.history']
                history.create({'last_sync': datetime.now(),
                                'no_ex_calender': 0,
                                'no_up_calender': 0,
                                'sync_type': 'manual' if is_manual else 'auto',
                                'no_up_task': len(update_task) if update_task else 0,
                                'no_up_contact': 0,
                                'no_ex_contact': 0,
                                'no_ex_email': 0,
                                'no_ex_task': len(export_task) if export_task else 0,
                                'sync_export_id': 1,
                                'status': status if status else 'Success'
                                })
                self.env.cr.commit()
        else:
            raise Warning("Token not found! Please Go to user preference from left corner and login Office365 Account ")

    @api.model
    def auto_import_tasks(self):
        self.import_tasks(is_manual=False)
    @api.model
    def auto_export_tasks(self):
        self.export_tasks(is_manual=False)


    # Mail

    def developer_test(self):
        try:
            channel = self.env['mail.channel'].search()
            raise osv.except_osv(_("Error!"), (_(channel)))
        except Exception as e:
            _logger.error(e)
            # res_user.send_mail_flag = True
            self.env.cr.commit()
            raise ValidationError(_(str(e)))
        self.env.cr.commit()
    def getAttachment(self, message):
        context = self._context
        current_uid = context.get('uid')
        if current_uid == None:
            office_connector = self.env['office.sync'].search([])[0]
            no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(no)
        else:
            res_user = self.env['res.users'].sudo().browse(current_uid)

        # res_user = self.env['res.users'].sudo().browse(current_uid)
        self.refresh_token(res_user)

        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages/' + message['id'] + '/attachments/',
            headers={
                'Host': 'outlook.office.com',
                'Authorization': 'Bearer {0}'.format(res_user.token),
                'Accept': 'application/json',
                'X-Target-URL': 'http://outlook.office.com',
                'connection': 'keep-Alive'
            }).content
        attachments = json.loads((response.decode('utf-8')))['value']
        attachment_ids = []
        for attachment in attachments:
            if 'contentBytes' not in attachment or 'name' not in attachment:
                continue
            odoo_attachment = self.env['ir.attachment'].create({
                'datas': attachment['contentBytes'],
                'name': attachment["name"],
                'store_fname': attachment["name"]})
            self.env.cr.commit()
            attachment_ids.append(odoo_attachment.id)
        return attachment_ids

    @api.model
    def sync_customer_mail_scheduler(self):
        self.sync_customer_mail(is_manual=False)
    def sync_customer_mail(self, is_manual=None):
        try:
            office_connector = self.env['office.sync'].search([])[0]

            if not is_manual:
                no = int(office_connector.for_auto_user_id)
                res_user = self.env['res.users'].sudo().browse(no)
            else:
                context = self._context
                current_uid = context.get('uid')
                res_user = self.env['res.users'].sudo().browse(current_uid)

            self.env.cr.commit()
            self.sync_customer_inbox_mail(is_manual)
            self.sync_customer_sent_mail(is_manual)
            res_user.last_mail_import = datetime.now()

        except Exception as e:
            self.env.cr.commit()
            raise ValidationError(_(str(e)))
        self.env.cr.commit()
    def sync_customer_inbox_mail(self, is_manual=None):

        office_connector = self.env['office.sync'].search([])[0]

        if not is_manual:
            no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(no)
        else:
            context = self._context
            current_uid = context.get('uid')
            res_user = self.env['res.users'].sudo().browse(current_uid)

        new_email = []
        status = None
        if res_user.token:
            try:
                self.refresh_token(res_user)
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/mailFolders',
                    headers={
                        'Authorization': 'Bearer {0}'.format(res_user.token),
                        'Content-type': 'application/json',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv("Access TOken Expired!", " Please Regenerate Access Token !")
                folders = json.loads((response.decode('utf-8')))['value']
                inbox_id = [folder['id'] for folder in folders if folder['displayName'] == 'Inbox']
                if inbox_id:
                    inbox_id = inbox_id[0]
                    url = ''
                    if is_manual:
                        if self.from_date and self.to_date:
                            url = 'https://graph.microsoft.com/v1.0/me/mailFolders/' + inbox_id + \
                                  '/messages?$top=1000&$count=true&$filter=ReceivedDateTime ge {} and ReceivedDateTime le {}' \
                                      .format(self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                        else:
                            url = 'https://graph.microsoft.com/v1.0/me/mailFolders/' + inbox_id + '/messages?$top=1000&$count=true'
                    else:
                        custom_data = self.env['office.sync'].search([])[0]
                        if custom_data.from_date and custom_data.to_date:
                            url = 'https://graph.microsoft.com/v1.0/me/mailFolders/' + inbox_id + \
                                  '/messages?$top=1000&$count=true&$filter' \
                                  '=ReceivedDateTime ge {} and ReceivedDateTime le {}' \
                                      .format(custom_data.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              custom_data.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                        elif res_user.last_mail_import:
                            url = 'https://graph.microsoft.com/v1.0/me/mailFolders/' + inbox_id + \
                                  '/messages?$top=1000&$count=' \
                                  'true&$filter=ReceivedDateTime ge {} and ReceivedDateTime le {}' \
                                      .format(res_user.last_mail_import.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
                        else:
                            url = 'https://graph.microsoft.com/v1.0/me' \
                                  '/mailFolders/' + inbox_id + '/messages?$top=1000&$count=true'

                    response = requests.get(url,
                                            headers={
                                                'Authorization': 'Bearer {0}'.format(res_user.token),
                                                'Content-type': 'application/json',
                                                'connection': 'keep-Alive'
                                            }).content
                    if 'value' not in json.loads((response.decode('utf-8'))).keys():
                        raise osv.except_osv("Access TOken Expired!", " Please Regenerate Access Token !")

                    else:
                        messages = json.loads((response.decode('utf-8')))['value']
                        for message in messages:
                            if 'from' not in message.keys() or self.env['mail.mail'].search(
                                    [('office_id', '=', message['id'])]) or self.env['mail.message'].search(
                                [('office_id', '=', message['id'])]):
                                continue

                            if 'address' not in message.get('from').get('emailAddress') or message['bodyPreview'] == "":
                                continue

                            attachment_ids = self.getAttachment(message)

                            from_partner = self.env['res.partner'].search(
                                [('email', "=", message['from']['emailAddress']['address'])])
                            if not from_partner:
                                continue
                            from_partner = from_partner[0] if from_partner else from_partner
                            recipient_partners = []
                            channel_ids = []
                            for recipient in message['toRecipients']:
                                if recipient['emailAddress'][
                                    'address'].lower() == res_user.office365_email.lower() or \
                                        recipient['emailAddress'][
                                            'address'].lower() == res_user.office365_id_address.lower():
                                    to_user = self.env['res.users'].search(
                                        [('id', "=", self._uid)])
                                else:
                                    to = recipient['emailAddress']['address']
                                    to_user = self.env['res.users'].search(
                                        [('office365_id_address', "=", to)])
                                    to_user = to_user[0] if to_user else to_user

                                if to_user:
                                    to_partner = to_user.partner_id
                                    recipient_partners.append(to_partner.id)
                            date = datetime.strptime(message['sentDateTime'], "%Y-%m-%dT%H:%M:%SZ")
                            self.env['mail.message'].create({
                                'subject': message['subject'],
                                'date': date,
                                'body': message['bodyPreview'],
                                'email_from': message['from']['emailAddress']['address'],
                                'partner_ids': [[6, 0, recipient_partners]],
                                'attachment_ids': [[6, 0, attachment_ids]],
                                'office_id': message['id'],
                                'author_id': from_partner.id,
                                'model': 'res.partner',
                                'res_id': from_partner.id
                            })
                            new_email.append(message['id'])
                            self.env.cr.commit()
            except Exception as e:
                # res_user.send_mail_flag = True
                status = 'Error'
                _logger.error(e)
                raise ValidationError(_(str(e)))

            finally:
                Type = None
                if not is_manual:
                    Type = 'auto'
                else:
                    Type = 'manual'
                history = self.env['sync.history'].search([])
                history.create({'last_sync': datetime.now(),
                                'no_im_email': len(new_email) if new_email else 0,
                                'status': status if status else 'Success',
                                'sync_type': Type,
                                'no_up_task': 0,
                                'no_up_contact': 0,
                                'no_im_contact': 0,
                                'no_im_calender': 0,
                                'no_up_calender': 0,
                                'no_im_task': 0,
                                'sync_id': 1,
                                })

                self.env.cr.commit()
        else:
            raise Warning("Token not found! Please Go to user preference from left corner and login Office365 Account ")
    def sync_customer_sent_mail(self, is_manual=None):
        """
        :return:
        """
        office_connector = self.env['office.sync'].search([])[0]

        if not is_manual:
            no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(no)
        else:
            context = self._context
            current_uid = context.get('uid')
            res_user = self.env['res.users'].sudo().browse(current_uid)

        if res_user.token:
            try:
                self.refresh_token(res_user)

                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/mailFolders',
                    headers={
                        'Authorization': 'Bearer {0}'.format(res_user.token),
                        'Content-type': 'application/json',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv("Access Token Expired!", " Please Regenerate Access Token !")
                else:
                    folders = json.loads((response.decode('utf-8')))['value']
                    sentbox_folder_id = [folder['id'] for folder in folders if folder['displayName'] == 'Sent Items']
                    if sentbox_folder_id:
                        sentbox_id = sentbox_folder_id[0]
                        response = requests.get(
                            'https://graph.microsoft.com/v1.0/me/mailFolders/' + sentbox_id + '/messages?$top=100000&$count=true',
                            headers={
                                'Authorization': 'Bearer {0}'.format(res_user.token),
                                'Content-type': 'application/json',
                                'connection': 'keep-Alive'
                            }).content
                        if 'value' not in json.loads((response.decode('utf-8'))).keys():

                            raise osv.except_osv("Access Token Expired!", " Please Regenerate Access Token !")
                        else:
                            messages = json.loads((response.decode('utf-8')))['value']
                            for message in messages:
                                # print(message['bodyPreview'])

                                if 'from' not in message.keys() or self.env['mail.mail'].search(
                                        [('office_id', '=', message['conversationId'])]) or self.env[
                                    'mail.message'].search(
                                    [('office_id', '=', message['conversationId'])]):
                                    continue

                                if message['bodyPreview'] == "":
                                    continue

                                attachment_ids = self.getAttachment(message)
                                if message['from']['emailAddress'][
                                    'address'].lower() == res_user.office365_email.lower() or \
                                        message['from']['emailAddress'][
                                            'address'].lower() == res_user.office365_id_address.lower():
                                    email_from = res_user.email
                                else:
                                    email_from = message['from']['emailAddress']['address']

                                from_user = self.env['res.users'].sudo().search(
                                    [('id', "=", self._uid)])
                                if from_user:
                                    from_partner = from_user.partner_id
                                else:
                                    continue

                                channel_ids = []
                                for recipient in message['toRecipients']:

                                    to_partner = self.env['res.partner'].search(
                                        [('email', "=", recipient['emailAddress']['address'])])
                                    to_partner = to_partner[0] if to_partner else to_partner

                                    if not to_partner:
                                        continue
                                    date = datetime.strptime(message['sentDateTime'], "%Y-%m-%dT%H:%M:%SZ")
                                    self.env['mail.message'].create({
                                        'subject': message['subject'],
                                        'date': date,
                                        'body': message['bodyPreview'],
                                        'email_from': email_from,
                                        'partner_ids': [[6, 0, [to_partner.id]]],
                                        'attachment_ids': [[6, 0, attachment_ids]],
                                        'office_id': message['conversationId'],
                                        'author_id': from_partner.id,
                                        'model': 'res.partner',
                                        'res_id': to_partner.id
                                    })
                                    self.env.cr.commit()

            except Exception as e:
                _logger.error(e)
                raise ValidationError(_(str(e)))
        else:
            raise Warning("Token not found! Please Go to user preference from left corner and login Office365 Account ")

     
    # Contacts

    def create_contacts(self, url,is_manual=None):
        
        office_contacts = []
        update_contact = []
        office_connector = self.env['office.sync'].search([])[0]
        if not is_manual:
            # no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(self.env.user.id)
        else:
            context = self._context
            current_uid = context.get('uid')
            res_user = self.env['res.users'].sudo().browse(current_uid)


        if not res_user.token:
            res_user = self.env['ir.cron'].search([('name', '=', 'Auto export Office365 contacts')]).user_id


        status = None
        if res_user.token:
            try:
                if res_user.token:
                    self.refresh_token(res_user)

                    headers = {
                        'Authorization': 'Bearer {0}'.format(res_user.token),
                        'Accept': 'application/json',
                        'connection': 'keep-Alive'}

                    while True:
                        response = requests.get(
                            url, headers=headers
                        ).content
                        response = json.loads(response.decode('utf-8'))
                        if not 'value' in response or not response['value']:
                            if not response['value']:
                                _logger.info("Contacts don't exist in Your Office365 account")
                            break
                        phone = None
                        if 'value' in response:
                            for each_contact in response['value']:
   
                                odoo_cust = self.env['res.partner'].search([('office_contact_id', '=', each_contact['id'])])
                                
                                if not odoo_cust:
                                    # self.add_contact(each_contact, res_user, office_contacts, phone)
                                    office_home_address = each_contact.get('homeAddress', None)
                                    office_state = each_contact['homeAddress'].get('state', None)
                                    state_id = self.get_state_id(each_contact, office_home_address, office_state)
                                    email_address = "No name"
                                    categ_id = None

                                    if 'categories' in each_contact and each_contact['categories']:
                                        categ_id = self.get_categ_id_contacts(each_contact)

                                    odoo_cust = self.env['res.partner'].create({
                                        'is_update': False,
                                        'modified_date': datetime.strptime(datetime.strftime(p.parse(
                                            each_contact['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                                            "%Y-%m-%dT%H:%M:%S"),
                                        'company_id': res_user.company_id.id,
                                        'name': each_contact[
                                            'displayName'] if 'displayName' in each_contact else
                                        email_address,
                                        'email': each_contact['emailAddresses'][0]['address'] if len(each_contact['emailAddresses']) > 0 and 'address' in each_contact['emailAddresses'][0] else None,
                                        'company_name': each_contact[
                                            'companyName'] if 'companyName' in each_contact else None,
                                        'function': each_contact[
                                            'jobTitle'] if 'jobTitle' in each_contact else None,
                                        'office_contact_id': each_contact['id'],
                                        'phone': each_contact['mobilePhone'] if 'mobilePhone' in each_contact else None,
                                        'street': each_contact['homeAddress']['street'] if 'street' in each_contact[
                                            'homeAddress'] and each_contact['homeAddress']  else None,
                                        'city': each_contact['homeAddress']['city'] if 'city' in
                                                                                    each_contact[
                                                                                        'homeAddress'] and
                                                                                    each_contact[
                                                                                        'homeAddress'] else None,
                                        'zip': each_contact['homeAddress']['postalCode'] if 'postalCode' in
                                                                                            each_contact[
                                                                                                'homeAddress'] and
                                                                                            each_contact[
                                                                                                'homeAddress'] else None,
                                        'state_id': state_id if office_home_address and office_state else None,
                                        'country_id': self.env['res.country'].search(
                                            [('name', '=',
                                            each_contact['homeAddress']['countryOrRegion'])]).id if 'countryOrRegion' in 
                                            each_contact['homeAddress'] and each_contact['homeAddress']  else None,
                                        'location': 'Office365 Contact',
                                        'category_id': [[6, 0, categ_id]] if categ_id else None,
                                    })
                                    office_contacts.append(odoo_cust)
                                    self.env.cr.commit()
                                    
                                    
                                else:
                                    if odoo_cust.modified_date == datetime.strptime(datetime.strftime(p.parse(each_contact['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),"%Y-%m-%dT%H:%M:%S"):
                                        continue
                                    else:
                                        # self.update_contact(odoo_cust, each_contact, res_user, update_contact, phone)
                                        office_home_address = each_contact.get('homeAddress', None)
                                        office_state = each_contact['homeAddress'].get('state', None)
                                        state_id = self.get_state_id(each_contact, office_home_address, office_state)
                                        email_address = "No name"
                                        categ_id = None

                                        if 'categories' in each_contact and each_contact['categories']:
                                            categ_id = self.get_categ_id_contacts(each_contact)

                                        odoo_cust.write({
                                            'is_update': False,
                                            'modified_date': datetime.strptime(datetime.strftime(p.parse(
                                                each_contact['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                                                "%Y-%m-%dT%H:%M:%S"),
                                            'company_id': res_user.company_id.id,
                                            'name': each_contact[
                                                'displayName'] if 'displayName' in each_contact else
                                            email_address,
                                            'email': each_contact['emailAddresses'][0]['address'] if len(each_contact['emailAddresses']) > 0 and 'address' in each_contact['emailAddresses'][0] else None,
                                            'company_name': each_contact[
                                                'companyName'] if 'companyName' in each_contact else None,
                                            'function': each_contact[
                                                'jobTitle'] if 'jobTitle' in each_contact else None,
                                            'office_contact_id': each_contact['id'],
                                            'phone': each_contact['mobilePhone'] if 'mobilePhone' in each_contact else None,
                                            'street': each_contact['homeAddress']['street'] if 'street' in each_contact[
                                                'homeAddress'] and each_contact['homeAddress']  else None,
                                            'city': each_contact['homeAddress']['city'] if 'city' in
                                                                                        each_contact[
                                                                                            'homeAddress'] and
                                                                                        each_contact[
                                                                                            'homeAddress'] else None,
                                            'zip': each_contact['homeAddress']['postalCode'] if 'postalCode' in
                                                                                                each_contact[
                                                                                                    'homeAddress'] and
                                                                                                each_contact[
                                                                                                    'homeAddress'] else None,
                                            'state_id': state_id if office_home_address and office_state else None,
                                            'country_id': self.env['res.country'].search(
                                                [('name', '=',
                                                each_contact['homeAddress']['countryOrRegion'])]).id if 'countryOrRegion' in 
                                                each_contact['homeAddress'] and each_contact['homeAddress']  else None,
                                            'location': 'Office365 Contact',
                                            'category_id': [[6, 0, categ_id]] if categ_id else None,
                                        })
                                        update_contact.append(odoo_cust)
                                        self.env.cr.commit()
                                        

                            if '@odata.nextLink' in response:
                                url = response['@odata.nextLink']
                            else:
                                break

                else:
                    raise Warning(
                        "Token not found! Please Go to user preference from left corner and login Office365 Account "
                    )
            except Exception as e:
                _logger.error(e)
                status = 'error'
                raise ValidationError(_(str(e)))
        else:
            raise Warning("Token not found! Please Go to user preference from left corner and login Office365 Account ")

        return office_contacts,update_contact      
    def import_contacts(self, is_manual=None):

        url = ''
        office_contacts = []
        update_contact = []
        status = None

        if self.contact_categories and not self.from_date and not self.to_date:
            for catg in self.contact_categories:
                url = 'https://graph.microsoft.com/v1.0/me/' \
                    "contacts?$filter=categories/any(a:a+eq+'{}')".format(catg.name.replace(' ', '+'))
                office_contacts,update_contact = self.create_contacts(url)
        
        
        elif is_manual and not self.contact_categories:
            if self.from_date and not self.to_date:
                raise Warning('Please! Select "To Date" to Import Events.')
            if self.from_date and self.to_date:
                url = 'https://graph.microsoft.com/v1.0/me/' \
                    'contacts?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}'.format(
                    self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                office_contacts,update_contact = self.create_contacts(url)
            else:
                url = 'https://graph.microsoft.com/v1.0/me/contacts'
                office_contacts,update_contact = self.create_contacts(url)


        elif self.contact_categories and self.from_date and self.to_date:
            for catg in self.contact_categories:
                url = 'https://graph.microsoft.com/v1.0/me/' \
                    'contacts?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}'.format(
                    self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ") + " and categories/any(a:a+eq+'{}')".format(catg.name.replace(' ', '+')))
                office_contacts,update_contact = self.create_contacts(url)
        

        else:
            # custom_data = self.env['office.sync'].search([])[0]
            # if custom_data.from_date and custom_data.to_date:
            #     url = 'https://graph.microsoft.com/v1.0/me/contacts' \
            #         '?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}'.format(
            #         custom_data.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            #         custom_data.to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            #     )
            #     office_contacts,update_contact = self.import_contacts_data(url)
            
            # elif res_user.last_contact_import:
            #     url = 'https://graph.microsoft.com/v1.0/me/contacts?$filter=' \
            #         'lastModifiedDateTime ge {} and lastModifiedDateTime le {}'.format(
            #         res_user.last_contact_import.strftime("%Y-%m-%dT%H:%M:%SZ"),
            #         datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            #     )
            #     office_contacts,update_contact = self.import_contacts_data(url)
            
            # else:
            url = 'https://graph.microsoft.com/v1.0/me/contacts'
            office_contacts,update_contact = self.create_contacts(url)

        self.insert_history_line(len(office_contacts), len(update_contact), is_manual, status, 'contacts')
    def export_contacts(self, is_manual=None):

        office_connector = self.env['office.sync'].search([])[0]
        if not is_manual:
            # no = int(office_connector.for_auto_user_id)
            res_user = self.env['res.users'].sudo().browse(self._context.get('uid'))
        else:
            context = self._context
            current_uid = context.get('uid')
            res_user = self.env['res.users'].sudo().browse(current_uid)

        if not res_user.token:
            res_user = self.env['ir.cron'].search([('name', '=', 'Auto export Office365 contacts')]).user_id

        new_contact = []
        update_contact = []
        status = None
        if res_user.token:
            try:
                if res_user.token:
                    self.refresh_token(res_user)

                    from_date = None
                    to_date = None

                    if is_manual:
                        if self.from_date and not self.to_date:
                            raise Warning('Please! Select "To Date" to Import Events.')
                        if self.from_date and self.to_date:
                            from_date = self.from_date
                            to_date = self.to_date
                        else:
                            if res_user.last_contact_import:
                                from_date = res_user.last_contact_import
                                to_date = datetime.now()

                    else:
                        custom_data = self.env['office.sync'].search([])[0]
                        if custom_data.from_date and custom_data.to_date:
                            from_date = custom_data.from_date
                            to_date = custom_data.to_date
                        elif res_user.last_contact_import:
                            from_date = res_user.last_contact_import
                            to_date = datetime.now()

                    # odoo_contacts = self.env['res.partner'].search(
                    #     [
                    #         '|',
                    #         ('company_id', '=', res_user.company_id.id),
                    #         ('company_id', '=', None)
                    #     ]

                    # odoo_contacts = self.env['res.partner'].search([("create_uid", '=', res_user.id)])

                    odoo_contacts = self.env['res.partner'].search([])

                    if from_date and to_date:
                        odoo_contacts = odoo_contacts.search([('write_date', '>=', from_date),('write_date', '<=', to_date),('is_update', '=', True)])

                    office_contact = []
                    count = 0
                    if odoo_contacts:
                        url_count = 'https://graph.microsoft.com/beta/me/contacts?$count = true'

                        headers = {
                            'Host': 'outlook.office365.com',
                            'Authorization': 'Bearer {0}'.format(res_user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'connection': 'keep-Alive'
                        }

                        response_count = requests.get(
                            url_count, headers=headers
                        ).content

                        response_count = json.loads(response_count.decode('utf-8'))
                        if '@odata.count' in response_count and response_count['@odata.count'] != -1:
                            count = response_count['@odata.count']


                        url = 'https://graph.microsoft.com/v1.0/me/contacts?$top=' + str(count)

                        response = requests.get(
                            url, headers=headers
                        ).content
                        response = json.loads(response.decode('utf-8'))
                        if not 'value' in response:
                            raise osv.except_osv("Access Token Expired!", " Please Regenerate Access Token !")

                        if 'value' in response:
                            contacts_emails = [response['value'][i]['emailAddresses'] for i in
                                               range(len(response['value']))]
                            for cont in contacts_emails:
                                if cont:
                                    office_contact.append(cont[0]['address'])

                        for contact in odoo_contacts:
                            company = None

                            # if not contact.email  in office_contact:

                            if contact.company_name:
                                company = contact.company_name
                            elif contact.parent_id.name:
                                company = contact.parent_id.name

                            data = {
                                "givenName": contact.name if contact.name else None,
                                'companyName': company,
                                'mobilePhone': contact.mobile if contact.mobile else None,
                                'jobTitle': contact.function if contact.function else None,
                                "businessPhones": [
                                    contact.phone if contact.phone else None
                                ]
                            }
                            if contact.email:
                                data["emailAddresses"] = [
                                    {
                                        "address": contact.email,
                                    }
                                ]
                            data["homeAddress"] = {
                                "street": contact.street if contact.street else (
                                    contact.street2 if contact.street2 else None),
                                "city": contact.city if contact.city else None,
                                "state": contact.state_id.name if contact.state_id else None,
                                "countryOrRegion": contact.country_id.name if contact.country_id else None,
                                "postalCode": contact.zip if contact.zip else None
                            }
                            if not contact.email and not contact.mobile and not contact.phone:
                                continue

                            contact_email = str(contact.email)

                            # if contact_office_contact_id or contact_email in office_contact:
                            if contact_email in office_contact:
                                if contact.create_date < contact.write_date and contact.is_update:
                                    if contact.office_contact_id:
                                        url = "https://graph.microsoft.com/v1.0/me/contacts/{}".format(
                                            contact.office_contact_id)
                                        response = requests.get(
                                            url,
                                            headers={
                                                'Host': 'outlook.office.com',
                                                'Authorization': 'Bearer {0}'.format(res_user.token),
                                                'Accept': 'application/json',
                                                'X-Target-URL': 'http://outlook.office.com',
                                                'connection': 'keep-Alive'
                                            }).content
                                        res_event = json.loads((response.decode('utf-8')))
                                        if 'id' not in res_event.keys():
                                            raise osv.except_osv(("Access Token Expired!"),
                                                                 (" Please Regenerate Access Token !"))
                                        modified_at = datetime.strptime(
                                            res_event['lastModifiedDateTime'][:-1], '%Y-%m-%dT%H:%M:%S'
                                        )
                                        if modified_at > contact.modified_date or modified_at == contact.modified_date:
                                            return
                                        update_response = requests.patch(
                                            'https://graph.microsoft.com/v1.0/me/contacts/' + str(
                                                contact.office_contact_id), data=json.dumps(data), headers=headers
                                        )
                                        if update_response.status_code != 200:
                                            pass
                                        else:
                                            response = json.loads(update_response.content)
                                            contact.write({'office_contact_id': response['id']})
                                            update_contact.append(response['id'])
                                        contact.is_update = False
                                else:
                                    continue

                            else:

                                post_response = requests.post(
                                    'https://graph.microsoft.com/v1.0/me/contacts', data=json.dumps(data),
                                    headers=headers
                                ).content

                                if 'id' not in json.loads(post_response.decode('utf-8')).keys():
                                    raise osv.except_osv(_("Error!"), (_(post_response["error"])))
                                else:
                                    response = json.loads(post_response.decode('utf-8'))
                                    contact.write({'office_contact_id': response['id']})
                                    contact.is_update = False
                                    new_contact.append(response['id'])

                else:
                    raise Warning(
                        "Token not found! Please Go to user preference from left corner and login Office365 Account "
                    )

            except Exception as e:
                _logger.error(e)
                status = "Error"
                raise ValidationError(_(str(e)))
            finally:
                history = self.env['export.history']
                history.create({'last_sync': datetime.now(),
                                'no_ex_calender': 0,
                                'no_up_calender': 0,
                                'sync_type': 'manual' if is_manual else 'auto',
                                'no_up_task': 0,
                                'no_up_contact': len(update_contact) if update_contact else 0,
                                'no_ex_contact': len(new_contact) if new_contact else 0,
                                'no_ex_email': 0,
                                'no_ex_task': 0,
                                'sync_export_id': 1,
                                'status': status if status else 'Success'
                                })

                self.env.cr.commit()
        else:
            raise Warning("Token not found! Please Go to user preference from left corner and login Office365 Account ")

    @api.model
    def auto_import_contact(self):
        self.env.cr.commit()
        self.import_contacts(is_manual=False)
    @api.model
    def auto_export_contact(self):
        self.export_contacts(is_manual=False)

class ImportHistory(models.Model):
    _name = 'export.history'
    _description = "Export/History"
    _order = 'last_sync desc'
    last_sync = fields.Datetime(string="Last Sync", required=False, )
    no_ex_contact = fields.Integer(string="New Contacts", required=False, )
    no_up_contact = fields.Integer(string="Updated Contacts", required=False, )
    no_ex_email = fields.Integer(string="New Emails", required=False, )
    no_ex_task = fields.Integer(string="New Tasks", required=False, )
    no_up_task = fields.Integer(string="Updated Tasks", required=False, )
    no_up_calender = fields.Integer(string="Updated Events", required=False, )
    no_ex_calender = fields.Integer(string="New Events", required=False, )
    status = fields.Char('Status')
    sync_type = fields.Selection(string="Sync_type", selection=[('auto', 'Auto'), ('manual', 'Manual'), ],
                                 required=False, )

    # sync_import_id = fields.Many2one("office.sync", string="Sync reference", required=False, )
    sync_export_id = fields.Many2one("office.sync", string="Sync reference", required=False, )

class HistoryLine(models.Model):
    _name = 'sync.history'
    _description = "Sync/History"
    _order = 'last_sync desc'

    sync_id = fields.Many2one('office.sync', string='Partner Reference', required=True, ondelete='cascade',
                              index=True, copy=False)
    last_sync = fields.Datetime(string="Last Sync", required=False, )
    no_im_contact = fields.Integer(string="New Contacts", required=False, )
    no_up_contact = fields.Integer(string="Updated Contacts", required=False, )
    no_im_email = fields.Integer(string="New Emails", required=False, )
    no_im_task = fields.Integer(string="New Tasks", required=False, )
    no_up_task = fields.Integer(string="Updated Tasks", required=False, )
    no_up_calender = fields.Integer(string="Updated Events", required=False, )
    no_im_calender = fields.Integer(string="New Events", required=False, )
    status = fields.Char('Status')
    sync_type = fields.Selection(string="Sync Type", selection=[('auto', 'Auto'), ('manual', 'Manual'), ],
                                 required=False, )
