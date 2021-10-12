import logging
import re
from odoo.exceptions import ValidationError, Warning, UserError
from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
import requests
import json
from datetime import datetime
import time
from datetime import timedelta
import dateutil.parser as p
import traceback

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/]{3,}=*)([\'"])', re.I)
_import_history = {}


class Office365(models.Model):
    """
    This class give functionality to user for Office365 Integration
    """
    _name = 'office.sync'
    _description = "Office365 - Connector"
    _rec_name = 'name'

    name = fields.Char("Name", compute='_get_name')
    event_del_flag = fields.Boolean('Delete events from Office365 calendar when delete in Odoo.',
                                    groups="base.group_user")
    office365_event_del_flag = fields.Boolean('Delete event from Odoo, if the event is deleted from Office 365.',
                                              groups="base.group_user")
    customers_count = fields.Integer("Customer Count", compute='compute_count')
    tasks_count = fields.Integer("Tasks Count", compute='compute_count')
    events_count = fields.Integer("Events Count", compute='compute_count')
    res_user = fields.Many2one('res.users', string='User', default=lambda self:self.env.user.id, readonly=True)
    is_manual_sync = fields.Boolean(string="Custom Date Range", )
    is_auto_sync = fields.Boolean(string="Auto Scheduler", )
    is_import_contact = fields.Boolean()
    is_import_email = fields.Boolean()
    is_import_calendar = fields.Boolean()
    is_import_task = fields.Boolean()
    is_export_contact = fields.Boolean()
    is_export_calendar = fields.Boolean()
    is_export_task = fields.Boolean()
    from_date = fields.Datetime(string="From Date", required=False, )
    to_date = fields.Datetime(string="To Date", required=False, )
    is_manual_execute = fields.Boolean(string="Manual Execute", )
    categories = fields.Many2many('calendar.event.type', string='Select Event Category')
    contact_categories = fields.Many2many('res.partner.category', string='Select Contact Category')
    calendar_id = fields.Many2one(comodel_name="office.calendars", string="Office365 Calendars", required=False, )

    def compute_count(self):
        for record in self:
            record.customers_count = self.env['res.partner'].search_count([('office_contact_id', '!=', None)])
            record.tasks_count = self.env['mail.activity'].search_count([('office_id', '!=', None)])
            record.events_count = self.env['calendar.event'].search_count([('office_id', '!=', None)])

    def get_code(self):
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        redirect_url = IrConfigParameter.get_param('odoo_office365.redirect_url')
        client_id = IrConfigParameter.get_param('odoo_office365.client_id')
        client_secret = IrConfigParameter.get_param('odoo_office365.client_secret')
        login_url = IrConfigParameter.get_param('odoo_office365.login_url')

        if redirect_url and client_id and client_secret:
            return {
                'name': 'login',
                'view_id': False,
                "type": "ir.actions.act_url",
                'target': 'self',
                'url': login_url
            }
        else:
            raise ValidationError('Office 365 Credentials are missing. Please! ask admin to add credentials')

    def action_user_form_office_365(self):
        existing_configurations = self.env['office.sync'].sudo().search([
            ('res_user', '=', self.env.user.id)])
        context = dict(self._context)
        current_logged_in_uid = self._context.get('uid')
        # existing_configurations = self.search([('for_auto_user_id', '=', current_logged_in_uid)])
        data = {
            'name': 'Office365 Sync Mail and Contact',
            'res_model': 'office.sync',
            'target': 'current',
            'view_mode': 'form',
            'type': 'ir.actions.act_window'
        }
        if not existing_configurations:
            return data

        data['res_id'] = existing_configurations[0].id
        return data

    def _get_name(self):
        for i in self:
            i.name = self.env.user.name + "'s " + "Configuration"

    def previewScheduleAction(self):
        self.ensure_one()
        officeModel = self.env['ir.model'].search([('model', '=', 'office.sync')])

        return {
            'type': 'ir.actions.act_window',
            'name': 'Schedulers',
            'view_mode': 'tree',
            'res_model': 'ir.cron',
            'domain': [('model_id', '=', officeModel.id)],
            'context': "{'create': False}"
        }

    def get_customers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Office 365 Customers',
            'view_mode': 'tree',
            'res_model': 'res.partner',
            'domain': [('office_contact_id', '!=', None)],
            'context': "{'create': False}"
        }

    def get_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Office 365 Tasks',
            'view_mode': 'tree',
            'res_model': 'mail.activity',
            'domain': [('office_id', '!=', None)],
            'context': "{'create': False}"
        }

    def get_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Office 365 Events',
            'view_mode': 'tree',
            'res_model': 'calendar.event',
            'domain': [('office_id', '!=', None)],
            'context': "{'create': False}"
        }

    def insert_history_line(self, id, added, updated, is_manual, status, action):
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
                        'sync_id': id,
                        'no_up_task': 0,
                        'no_im_email': 0,
                        'no_im_calender': 0,
                        'no_up_calender': 0,
                        'no_im_task': 0,
                        'status': status if status else 'Success',

                        })
        self.env.cr.commit()

    def execute_operation(self):
        b = 50
        print(b)
        self.checkTokenExpiryDate(self.res_user)
        a = 25
        if self.is_manual_sync or self.is_auto_sync or not self.is_auto_sync:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            interval_number = IrConfigParameter.get_param('odoo_office365.interval_number')
            interval_unit = IrConfigParameter.get_param('odoo_office365.interval_unit')
            odooUser = self.res_user
            if odooUser.refresh_token:
                if self.is_import_contact or self.is_import_task or self.is_import_email or self.is_import_calendar:
                    if self.is_manual_sync:
                        self.import_data(False)

                    if self.is_auto_sync:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Import Office 365 Data')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Import Office 365 Data'),
                                                                    ('active', '=', False)])
                        scheduler.active = self.is_auto_sync
                        scheduler.interval_number = interval_number
                        scheduler.interval_type = interval_unit
                    else:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Import Office 365 Data')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Import Office 365 Data'),
                                                                    ('active', '=', False)])
                        scheduler.active = self.is_auto_sync

                if self.is_export_task or self.is_export_contact or self.is_export_calendar:
                    if self.is_manual_sync:
                        self.export_data(False)

                    if self.is_auto_sync:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Export Odoo Data')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Export Odoo Data'),
                                                                    ('active', '=', False)])
                        scheduler.active = self.is_auto_sync
                        scheduler.interval_number = interval_number
                        scheduler.interval_type = interval_unit
                    else:
                        scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Export Odoo Data')])
                        if not scheduler:
                            scheduler = self.env['ir.cron'].search([('name', '=', 'Auto Export Odoo Data'),
                                                                    ('active', '=', False)])
                        scheduler.active = self.is_auto_sync

                if not self.is_import_contact and not self.is_import_task and not self.is_import_email \
                        and not self.is_import_calendar and not self.is_export_task and not self.is_export_contact \
                        and not self.is_export_calendar:
                    raise ValidationError('No operation utility is selected.')
            else:
                raise ValidationError('Please login with your Office 365 account to perform operation')
        else:
            raise ValidationError('Please specify the type of operation.')

    def auto_import(self):
        activeAutoImportSettings = self.env['office.sync'].search([('is_auto_sync', '=', True)])
        for activeAutoImportSetting in activeAutoImportSettings:
            self.import_data(True, activeAutoImportSetting)

    def auto_export(self):
        activeAutoExportSettings = self.env['office.sync'].search([('is_auto_sync', '=', True)])
        for activeAutoExportSetting in activeAutoExportSettings:
            self.export_data(True, activeAutoExportSetting)

    def import_data(self, auto, setting=None):
        data_dictionary = {}

        status = 'import'
        sync_type = 'manual'

        if auto:
            self = setting
            sync_type = 'scheduled'

        self.checkTokenExpiryDate(self.res_user)

        if self.is_import_contact:
            data_dictionary["importContacts"] = self.import_contacts()
        if self.is_import_task:
            data_dictionary["importTasks"] = self.import_tasks()
        if self.is_import_email:
            data_dictionary["importEmails"] = self.sync_customer_mail()
        if self.is_import_calendar:
            data_dictionary["importCalendars"] = self.import_calendar()

        self.env['sync.history'].create({
            'user_id' : self.res_user.id,
            'last_sync' : datetime.now(),
            'numberContacts' : data_dictionary['importContacts']['importedContacts'] if 'importContacts' in data_dictionary else None,
            'numberContactsUpdated' : data_dictionary['importContacts']['updatedContacts'] if 'importContacts' in data_dictionary else None,
            'numberEmails' : data_dictionary['importEmails']['importedEmails'] if 'importEmails' in  data_dictionary else None,
            'numberTasks' : data_dictionary['importTasks']['importedTasks'] if 'importTasks' in data_dictionary else None,
            'numberTasksUpdated' : data_dictionary['importTasks']['updatedTasks'] if 'importTasks' in data_dictionary else None,
            'numberCalendars' : data_dictionary['importCalendars']['importedCalendars'] if 'importCalendars' in data_dictionary else None,
            'numberCalendarsUpdated' : data_dictionary['importCalendars']['updatedCalendars'] if 'importCalendars' in data_dictionary else None,
            'status' : status,
            'sync_type': sync_type,
        })
        self.env.cr.commit()

    def export_data(self, auto, setting=None):
        data_dictionary = {}

        status = 'export'
        sync_type = 'manual'

        if auto:
            self = setting
            sync_type = 'scheduled'

        self.checkTokenExpiryDate(self.res_user)

        if self.is_export_task:
            data_dictionary["exportTasks"] = self.export_tasks()
        if self.is_export_contact:
            data_dictionary["exportContacts"] = self.export_contacts()
        if self.is_export_calendar:
            data_dictionary["exportCalendars"] = self.export_calendar()

        self.env['sync.history'].create({
            'user_id' : self.res_user.id,
            'last_sync' : datetime.now(),
            'numberContacts' : data_dictionary['exportContacts']['exportedContacts'] if 'exportContacts' in data_dictionary else None,
            'numberContactsUpdated' : data_dictionary['exportContacts']['updatedContacts'] if 'exportContacts' in data_dictionary  else None,
            'numberEmails' : data_dictionary['exportEmails']['exportedEmails'] if 'exportEmails' in  data_dictionary else None,
            'numberTasks' : data_dictionary['exportTasks']['exportedTasks'] if 'exportTasks' in data_dictionary else None,
            'numberTasksUpdated' : data_dictionary['exportTasks']['updatedTasks'] if 'exportTasks' in data_dictionary else None,
            'numberCalendars' : data_dictionary['exportCalendars']['exportedCalenders'] if 'exportCalendars' in data_dictionary else None,
            'numberCalendarsUpdated' : data_dictionary['exportCalendars']['updatedCalenders'] if 'exportCalendars' in data_dictionary else None,
            'status' : status,
            'sync_type': sync_type,
            })
        self.env.cr.commit()

    ''' 
    These following methods are responsible fro importing contacts from Office 365
    '''
    def import_contacts(self):
        office_contacts = 0
        update_contact = 0

        if self.contact_categories:
            if not self.from_date and not self.to_date:
                for catg in self.contact_categories:
                    url = 'https://graph.microsoft.com/v1.0/me/contacts?$filter=categories/any(a:a+eq+\'{}\')'.format(catg.name.replace(' ', '+'))
                    office_contacts, update_contact = self.create_contacts(url)
            elif self.from_date and self.to_date:
                for catg in self.contact_categories:
                    url = 'https://graph.microsoft.com/v1.0/me/' \
                          'contacts?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}'.format(
                        self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ") + " and categories/any(a:a+eq+'{}')".format(
                            catg.name.replace(' ', '+')))
                    office_contacts, update_contact = self.create_contacts(url)
            else:
                raise ValidationError('Please select proper date range i.e. you have to select from and to date or '
                                      'else leave them blank')
        else:
            if not self.from_date and not self.to_date:
                url = 'https://graph.microsoft.com/v1.0/me/contacts'
                office_contacts, update_contact = self.create_contacts(url)
            elif self.from_date and self.to_date:
                url = 'https://graph.microsoft.com/v1.0/me/' \
                      'contacts?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}'.format(
                    self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                office_contacts, update_contact = self.create_contacts(url)
            else:
                raise ValidationError('Please select proper date range i.e. you have to select from and to date or '
                                      'else leave them blank')
        import_dictionary = {
            'importedContacts': office_contacts,
            'updatedContacts': update_contact
        }

        return import_dictionary

    def create_contacts(self, url):
        office_contacts = []
        update_contact = []
        headers = {
            'Authorization': 'Bearer {0}'.format(self.res_user.token),
            'Accept': 'application/json',
            'connection': 'keep-Alive'}

        while True:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                response = json.loads(response.content.decode('utf-8'))
                if 'value' in response:
                    for each_contact in response['value']:
                        odoo_customer = self.env['res.partner'].search([('office_contact_id', '=', each_contact['id'])])
                        name = None
                        categories_ids = None
                        street = None
                        city = None
                        zip = None
                        phone = None
                        if each_contact['displayName']:
                            firstname = each_contact['givenName'] if each_contact['givenName'] else ''
                            middlename = each_contact['middleName'] if each_contact['middleName'] else ''
                            lastname = each_contact['surname'] if each_contact['surname'] else ''
                            name = firstname + " " + middlename + " " + lastname
                            company_type = 'person'
                            if each_contact['homeAddress']:
                                street = each_contact['homeAddress']['street'] if 'street' in each_contact['homeAddress'] else ''
                                city = each_contact['homeAddress']['city'] if 'city' in each_contact['homeAddress'] else ''
                                zip = each_contact['homeAddress']['postalCode'] if 'postalCode' in each_contact['homeAddress'] else ''
                            if len(each_contact['homePhones']) > 0:
                                phone = each_contact['homePhones'][0]
                        else:
                            name = each_contact['companyName']
                            company_type = 'company'
                            if each_contact['businessAddress']:
                                street = each_contact['businessAddress']['street'] if 'street' in each_contact['businessAddress'] else ''
                                city = each_contact['businessAddress']['city'] if 'city' in each_contact['businessAddress'] else ''
                                zip = each_contact['businessAddress']['postalCode'] if 'postalCode' in each_contact['businessAddress'] else ''
                            if len(each_contact['businessPhones']) > 0:
                                phone = each_contact['businessPhones'][0]

                        if len(each_contact['categories']) > 0:
                            categories_ids = self.getContactsOdooCategory(each_contact['categories'])

                        officeModifiedDate = datetime.strptime(datetime.strftime(p.parse(each_contact['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),"%Y-%m-%dT%H:%M:%S")

                        if not odoo_customer:
                            odoo_cust = self.env['res.partner'].create({
                                'office_contact_id': each_contact['id'],
                                'modified_date': officeModifiedDate,
                                'company_id': self.res_user.company_id.id,
                                'company_type': company_type,
                                'name': name,
                                'firstName': each_contact['givenName'] if each_contact['givenName'] else '',
                                'lastName': each_contact['surname'] if each_contact['surname'] else '',
                                'middleName': each_contact['middleName'] if each_contact['middleName'] else '',
                                'function': each_contact['jobTitle'] if each_contact['jobTitle'] else None,
                                'phone': each_contact['businessPhones'][0] if each_contact['businessPhones'] else None,
                                'mobile': each_contact['mobilePhone'] if each_contact['mobilePhone'] else None,
                                'email': each_contact['emailAddresses'][0]['address'] if each_contact['emailAddresses'] else None,
                                'website': each_contact['businessHomePage'] if each_contact['businessHomePage'] else None,
                                'street': street,
                                'city': city,
                                'zip': zip,
                                'location': 'Office365 Contact',
                                'category_id': [[6, 0, categories_ids]] if categories_ids else None,
                            })
                            office_contacts.append(odoo_cust.id)

                        else:
                            if odoo_customer.modified_date:

                                if odoo_customer.modified_date >= officeModifiedDate:
                                    continue
                                else:
                                    odoo_customer.write({
                                        'office_contact_id': each_contact['id'],
                                        'modified_date': officeModifiedDate,
                                        'company_id': self.res_user.company_id.id,
                                        'company_type': company_type,
                                        'name': name,
                                        'firstName': each_contact['givenName'] if each_contact['givenName'] else '',
                                        'lastName': each_contact['surname'] if each_contact['surname'] else '',
                                        'middleName': each_contact['middleName'] if each_contact['middleName'] else '',
                                        'function': each_contact['jobTitle'] if each_contact['jobTitle'] else None,
                                        'phone': each_contact['businessPhones'][0] if each_contact['businessPhones'] else None,
                                        'mobile': each_contact['mobilePhone'] if each_contact['mobilePhone'] else None,
                                        'email': each_contact['emailAddresses'][0]['address'] if each_contact['emailAddresses'] else None,
                                        'website': each_contact['businessHomePage'] if each_contact['businessHomePage'] else None,
                                        'street': street,
                                        'city': city,
                                        'zip': zip,
                                        'location': 'Office365 Contact',
                                        'category_id': [[6, 0, categories_ids]] if categories_ids else None,
                                    })
                                    update_contact.append(odoo_customer.id)
                        self.env.cr.commit()
                    if '@odata.nextLink' in response:
                        url = response['@odata.nextLink']
                    else:
                        break
        return len(office_contacts), len(update_contact)

    ''' 
        These methods are responsible fro importing calendars from Office 365
    '''
    def import_calendar(self):
        try:
            new_event = 0
            update_event = 0
            if self.categories:
                if not self.from_date and not self.to_date:
                    for catg in self.categories:
                        if self.calendar_id and self.calendar_id.calendar_id:
                            url = "https://graph.microsoft.com/v1.0/me/calendars/" + str(
                                self.calendar_id.calendar_id) + "/events?$filter=categories/any(a:a+eq+'{}')".format(
                                catg.name.replace(' ', '+'))
                        else:
                            url = "https://graph.microsoft.com/v1.0/me/events?$filter=categories/any(a:a+eq+'{}')".format(
                                catg.name.replace(' ', '+'))
                        office_calendars, update_calendars = self.create_events(url)
                if self.from_date and self.to_date:
                    categ_name = []
                    for catg in self.categories:
                        if self.calendar_id:
                            url = "https://graph.microsoft.com/v1.0/me/calendars/" + str(
                                self.calendar_id.calendar_id) + "/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}".format(
                                self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"), self.to_date.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ")) + " and categories/any(a:a+eq+'{}')".format(
                                catg.name.replace(' ', '+'))
                        else:
                            url = "https://graph.microsoft.com/v1.0/me/calendars/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}".format(
                                self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"), self.to_date.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ")) + " and categories/any(a:a+eq+'{}')".format(
                                catg.name.replace(' ', '+'))

                        office_calendars, update_calendars = self.create_events(url)
            else:
                if self.from_date and self.to_date:
                    if self.calendar_id:
                        url = 'https://graph.microsoft.com/v1.0/me/calendars/' + str(
                            self.calendar_id.calendar_id) + '/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}' \
                                  .format(self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                          self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    else:
                        url = 'https://graph.microsoft.com/v1.0/me/events?$filter=lastModifiedDateTime%20gt%20{}%20and%20lastModifiedDateTime%20lt%20{}' \
                            .format(self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    office_calendars, update_calendars = self.create_events(url)

                if not self.from_date and not self.to_date:
                    if self.calendar_id and self.calendar_id.calendar_id:
                        url = 'https://graph.microsoft.com/v1.0/me/calendars/' + str(
                            self.calendar_id.calendar_id) + '/events'
                    else:
                        url = 'https://graph.microsoft.com/v1.0/me/events'

                    office_calendars, update_calendars = self.create_events(url)


            import_dictionary = {
                'importedCalendars': office_calendars,
                'updatedCalendars': update_calendars,
            }

            return import_dictionary

        except Exception as e:
            traceback.print_exc()
            raise ValidationError(str(e))

    def create_events(self, url):
        update_event = []
        new_event = []
        try:
            header = {
            'Authorization': 'Bearer {0}'.format(self.res_user.token),
            'Accept': 'application/json',
            'connection': 'keep-Alive'}
            while True:
                response = requests.get(url, headers=header)
                if response.status_code == 200:
                    responseDecoded = json.loads((response.content.decode('utf-8')))
                    events = responseDecoded['value']
                    for event in events:
                        odooEvent = self.env['calendar.event'].search([("office_id", "=", event['id'])])

                        categories_ids = None
                        if event['categories']:
                            categories_ids = self.getEventOdooCategory(event)

                        rRule = None
                        interval = None
                        if event['recurrence']:
                            if 'absolute' in event['recurrence']['pattern']['type']:
                                rRule = event['recurrence']['pattern']['type'].replace('absolute', '').lower()
                            elif 'relative' in event['recurrence']['pattern']['type']:
                                rRule = event['recurrence']['pattern']['type'].replace('relative', '').lower()

                            interval = event['recurrence']['pattern']['interval']

                        final_date = None
                        if event['recurrence']:
                            if event['recurrence']['range']['type'] == 'noEnd':
                                final_date = datetime.strptime(event['recurrence']['range']['startDate'],
                                                               '%Y-%m-%d').strftime('%Y-%m-%d')
                            else:
                                final_date = datetime.strptime(event['recurrence']['range']['endDate'],
                                                               '%Y-%m-%d').strftime('%Y-%m-%d')

                        partner_ids = []
                        if event['attendees']:
                            partner_ids = self.getEventOdooAttendees(event['attendees'])
                        else:
                            partner_ids.append(self.res_user.partner_id.id)

                        location = event['location']['displayName'] if 'displayName' in event['location'] else None

                        startDateTime = datetime.strptime(
                                    datetime.strftime(p.parse(event['start']['dateTime']), "%Y-%m-%dT%H:%M:%S"),
                                    "%Y-%m-%dT%H:%M:%S")
                        endDateTime = datetime.strptime(
                                    datetime.strftime(p.parse(event['end']['dateTime']), "%Y-%m-%dT%H:%M:%S"),
                                    "%Y-%m-%dT%H:%M:%S")

                        officeModifiedDate = datetime.strptime(datetime.strftime(p.parse(event['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),"%Y-%m-%dT%H:%M:%S")


                        if not odooEvent:
                            odooEvent = self.env['calendar.event'].create({
                                'office_id': event['id'],
                                'name': event['subject'],
                                'calendar_id': self.calendar_id.id if self.calendar_id else None,
                                'category_name': event['categories'][0] if event['categories'] else None,
                                "description": event['bodyPreview'],
                                'location': location,
                                'start': startDateTime,
                                'stop': endDateTime,
                                'allday': event['isAllDay'],
                                'categ_ids': [[6, 0, categories_ids]] if categories_ids else None,
                                'show_as': event['showAs'],
                                'recurrency': True if event['recurrence'] else False,
                                'interval': interval,
                                'end_type': 'end_date' if event['recurrence'] else "",
                                'rrule_type': rRule,
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
                                # 'month_by': day_date_selection,
                                # 'day': day,
                                # 'byday': index,
                                # 'weekday': week_day,
                                'partner_ids': [[6, 0, partner_ids]] if partner_ids else None
                            })
                            new_event.append(odooEvent.id)
                        else:
                            if odooEvent.modified_date:

                                if odooEvent.modified_date >= officeModifiedDate:
                                    continue
                                else:
                                    odooEvent.write({
                                        'office_id': event['id'],
                                        'name': event['subject'],
                                        'calendar_id': self.calendar_id.id if self.calendar_id else None,
                                        'category_name': event['categories'][0] if event['categories'] else None,
                                        "description": event['bodyPreview'],
                                        'location': location,
                                        'start': startDateTime,
                                        'stop': endDateTime,
                                        'allday': event['isAllDay'],
                                        'categ_ids': [[6, 0, categories_ids]] if categories_ids else None,
                                        'show_as': event['showAs'],
                                        'recurrency': True if event['recurrence'] else False,
                                        'end_type': 'end_date' if event['recurrence'] else "",
                                        'rrule_type': rRule,
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
                                        # 'month_by': day_date_selection,
                                        # 'day': day,
                                        # 'byday': index,
                                        # 'weekday': week_day,
                                        'partner_ids': [[6, 0, partner_ids]] if partner_ids else None
                                    })
                                    update_event.append(odooEvent.id)
                                self.env.cr.commit()


                    if '@odata.nextLink' in responseDecoded:
                        url = responseDecoded['@odata.nextLink']
                    else:
                        break

            return len(new_event), len(update_event),

        except Exception as e:
            traceback.print_exc()
            raise ValidationError(str(e))

    def getEventOdooAttendees(self, attendees):
        odooAttendees = []
        for attendee in attendees:
            if 'emailAddress' in attendee:
                partner = self.env['res.partner'].search([('email', "=", attendee['emailAddress']['address'])])
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': attendee['emailAddress']['name'],
                        'email': attendee['emailAddress']['address'],
                        'location': 'Office365 Attendee',
                    })
                    self.env.cr.commit()
                    odooAttendees.append(partner.id)
                else:
                    odooAttendees.append(partner[0].id)

        return odooAttendees

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

    ''' 
        These following methods are responsible fro importing tasks from Office 365
    '''
    def import_tasks(self):
        office_tasks = 0
        update_tasks = 0
        odooUser = self.env.user
        url = 'https://graph.microsoft.com/v1.0/me/todo/lists'
        header = {
            'Authorization': 'Bearer {0}'.format(odooUser.token),
            'Content-type': 'application/json',
            'connection': 'keep-Alive'
        }
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            res_data = json.loads((response.content.decode('utf-8')))
            for list in res_data['value']:
                new_url = 'https://graph.microsoft.com/v1.0/me/todo/lists/' + list['id'] + '/tasks'

                if not self.from_date and not self.to_date:
                    office_tasks, update_tasks = self.create_tasks(new_url)
                if self.from_date and self.to_date:
                    url = new_url + '?$filter=lastModifiedDateTime ge {} and lastModifiedDateTime le {}' \
                              .format(self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                      self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    office_tasks, update_tasks = self.create_tasks(url)

        import_dictionary = {
            'importedTasks': office_tasks,
            'updatedTasks': update_tasks,
        }

        return import_dictionary

    def create_tasks(self, url):
        try:
            new_tasks = []
            update_tasks = []
            headers = {
                'Authorization': 'Bearer {0}'.format(self.res_user.token),
                'Accept': 'application/json',
                'connection': 'keep-Alive'}
            while True:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    res_data = json.loads((response.content.decode('utf-8')))
                    tasks = res_data['value']
                    for task in tasks:
                        res_model_id = self.env.ref('odoo_office365.model_activity_general')
                        res_id = self.env.ref('odoo_office365.general_activities')
                        activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')])
                        odoo_task = self.env['mail.activity'].search([('office_id', '=', task['id'])])
                        dueDateTime = task['dueDateTime']['dateTime'][:-16] if 'dueDateTime' in task else None
                        officeModifiedDate = datetime.strptime(datetime.strftime(p.parse(task['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),"%Y-%m-%dT%H:%M:%S")

                        if not odoo_task:
                            odooTask = self.env['mail.activity'].create({
                                'res_id': res_id.id,
                                'activity_type_id': activity_type.id if activity_type else None,
                                'summary': task['title'],
                                'date_deadline': (datetime.strptime(dueDateTime, '%Y-%m-%dT')).strftime('%Y-%m-%d')
                                if dueDateTime else datetime.now(),
                                'note': task['body']['content'],
                                'res_model_id': res_model_id.id,
                                'office_id': task['id'],
                                'modified_date': datetime.strptime(datetime.strftime(p.parse(
                                    task['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                                    "%Y-%m-%dT%H:%M:%S"),
                            })
                            new_tasks.append(odooTask.id)

                        else:
                            if odoo_task.modified_date:

                                if odoo_task.modified_date >= officeModifiedDate:
                                    continue
                                
                                # elif odoo_task and task['status'] != 'completed':
                                else:
                                    odoo_task.write({
                                        'res_id': res_id.id,
                                        'activity_type_id': activity_type.id if activity_type else None,
                                        'summary': task['title'],
                                        'date_deadline': (datetime.strptime(dueDateTime, '%Y-%m-%dT')).strftime('%Y-%m-%d')
                                        if dueDateTime else datetime.now(),
                                        'note': task['body']['content'],
                                        'res_model_id': res_model_id.id,
                                        'office_id': task['id'],
                                        'modified_date': datetime.strptime(datetime.strftime(p.parse(
                                            task['lastModifiedDateTime']), "%Y-%m-%dT%H:%M:%S"),
                                            "%Y-%m-%dT%H:%M:%S"),
                                    })
                                    update_tasks.append(odoo_task.id)

                        self.env.cr.commit()

                    if '@odata.nextLink' in res_data:
                        url = res_data['@odata.nextLink']
                    else:
                        break
            return len(new_tasks), len(update_tasks)

        except Exception as e:
            raise ValidationError(_(str(e)))

    ''' 
        These following methods are responsible fro importing emails from Office 365
    '''
    def sync_customer_mail(self):
        odooUser = self.env.user
        url = 'https://graph.microsoft.com/v1.0/me/mailFolders'
        headers = {
            'Authorization': 'Bearer {0}'.format(odooUser.token),
            'Content-type': 'application/json',
            'connection': 'keep-Alive'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            folders = json.loads((response.content.decode('utf-8')))['value']
            folder_ids = [folder['id'] for folder in folders if folder['displayName'] == 'Sent Items' or folder['displayName'] == 'Inbox']
            for folder_id in folder_ids:
                if self.from_date and self.to_date:
                    url = 'https://graph.microsoft.com/v1.0/me/mailFolders/' + folder_id + \
                          '/messages?$top=1000&$count=true&$filter=ReceivedDateTime ge {} and ReceivedDateTime le {}' \
                              .format(self.from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                      self.to_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    office_emails = self.create_emails(url)
                if not self.from_date and not self.to_date:
                    url = 'https://graph.microsoft.com/v1.0/me/mailFolders/' + folder_id + '/messages?$top=1000&$count=true'
                    office_emails = self.create_emails(url)

        import_dictionary = {
            'importedEmails': office_emails,
            }

        return import_dictionary

    def create_emails(self, url):
        new_email = []
        attachment_ids = []
        headers = {
            'Authorization': 'Bearer {0}'.format(self.res_user.token),
            'Content-type': 'application/json',
            'connection': 'keep-Alive'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            messages = json.loads((response.content.decode('utf-8')))['value']
            for message in messages:
                odooMail = self.env['mail.message'].search([('office_id', '=', message['id'])])
                if not odooMail:
                    if self.checkrequired(message) == 0:
                        continue
                    if message['hasAttachments']:
                        attachment_ids = self.getAttachment(message)
                    from_partner = self.env['res.partner'].search([('email', "=", message['from']['emailAddress']['address'])])
                    if not from_partner:
                        continue
                    else:
                        from_partner = from_partner[0]
                    recipient_partners = []
                    for recipient in message['toRecipients']:
                        odooUser = self.env['res.users'].search([('email', '=', recipient['emailAddress']['address'].lower())])
                        if odooUser:
                            odooPartner = odooUser[0].partner_id
                            recipient_partners.append(odooPartner.id)

                    date = datetime.strptime(message['sentDateTime'], "%Y-%m-%dT%H:%M:%SZ")
                    newMail = self.env['mail.message'].create({
                        'subject': message['subject'],
                        'date': date,
                        'body': message['body']['content'] if 'content' in message['body'] else '',
                        'email_from': message['sender']['emailAddress']['address'],
                        'partner_ids': [[6, 0, recipient_partners]],
                        'attachment_ids': [[6, 0, attachment_ids]],
                        'office_id': message['id'],
                        'author_id': from_partner.id,
                        'model': 'res.partner',
                        'res_id': from_partner.id
                    })
                    self.env.cr.commit()

                    new_email.append(newMail.id)
            return len(new_email)

    def getAttachment(self, message):
        url = 'https://graph.microsoft.com/v1.0/me/messages/' + message['id'] + '/attachments/'
        header = {
                'Host': 'outlook.office.com',
                'Authorization': 'Bearer {0}'.format(self.res_user.token),
                'Accept': 'application/json',
                'X-Target-URL': 'http://outlook.office.com',
                'connection': 'keep-Alive'
            }

        response = requests.get(url, headers=header)
        if response.status_code == 200:
            attachments = json.loads((response.content.decode('utf-8')))['value']
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

    def checkrequired(self, message):
        if 'from' not in message.keys():
            return 0

        elif 'address' not in message.get('from').get('emailAddress') or message['bodyPreview'] == "":
            return 0
        else:
            return 1

    ''' 
        These following methods are responsible for managing token and refresh token
    '''

    def checkTokenExpiryDate(self, odooUser):
        if odooUser.expires_in:
            expires_in = datetime.fromtimestamp(int(odooUser.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            now = datetime.now()
            if now > expires_in:
                self.generate_refresh_token(odooUser)

    def generate_refresh_token(self, odooUser):
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        redirect_url = IrConfigParameter.get_param('odoo_office365.redirect_url')
        client_id = IrConfigParameter.get_param('odoo_office365.client_id')
        client_secret = IrConfigParameter.get_param('odoo_office365.client_secret')
        header = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        payload = 'grant_type=refresh_token&refresh_token=' + odooUser.refresh_token + \
                  '&redirect_uri=' + redirect_url + '&client_id=' + client_id + \
                  '&client_secret=' + client_secret
        response = requests.post(url, data=payload, headers=header)

        if response.status_code == 200:
            newToken = json.loads((response.content.decode('utf-8')))
            odooUser.write({
                'token': newToken['access_token'],
                'refresh_token': newToken['refresh_token'],
                'expires_in': int(round(time.time() * 1000))
            })
            self.env.cr.commit()
        else:
            raise ValidationError(str("Your Token has been expired and while updating automatically we are facing issue can you please "
                                      "check your credentials or again login with your Office 365 account"))

    ''' 
        These following methods are responsible for managing contact's and calendar's categories
    '''

    def getContactsOdooCategory(self, categories):
        categ_ids = []
        for category in categories:
            odooCategory = self.env['res.partner.category'].search([('name', '=', category)])[0]
            if odooCategory:
                categ_ids.append(odooCategory.id)
            else:
                newCategory = self.env['res.partner.category'].create({'name': category})
                categ_ids.append(newCategory.id)
        return categ_ids

    def getEventOdooCategory(self, event):
        categ_id = []
        for categ in event['categories']:
            categ_type_id = self.env['calendar.event.type'].search([('name', '=', categ)])
            if categ_type_id:
                categ_type_id.write({'name': categ})
                categ_id.append(categ_type_id[0].id)
            else:
                categ_type_id = categ_type_id.create({'name': categ})
                categ_id.append(categ_type_id[0].id)
        return categ_id

    ''' 
        This following method is responsible for exporting events from Odoo
    '''
    def export_calendar(self):
        export_event = []
        update_event = []
        try:
            res_user = self.res_user
            if self.from_date and not self.to_date:
                raise Warning('Please! Select "To Date" to Import Events.')
            if self.from_date and self.to_date:
                from_date = self.from_date
                to_date = self.to_date

            header = {
                'Authorization': 'Bearer {0}'.format(res_user.token),
                'Content-Type': 'application/json'
            }
            if self.calendar_id and self.calendar_id.calendar_id:
                calendar_id = self.calendar_id.calendar_id
            else:
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/calendars',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(res_user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    })

                if response.status_code == 200 or response.status_code == 201:
                    res_data = json.loads((response.content.decode('utf-8')))
                    calendars = res_data['value']
                    calendar_id = calendars[0]['id']

            # meetings = self.env['calendar.event'].search([("create_uid", '=', res_user.id)])
            meetings = self.env['calendar.event'].search([])
            if self.from_date and self.to_date:
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
                        event_type = (
                                         'Absolute' if meeting.rrule_type != "weekly" and meeting.rrule_type != "daily" else "") + meeting.rrule_type
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
                            headers=header, data=json.dumps(payload))
                        if 'id' in json.loads((response.content.decode('utf-8'))):
                            temp.write({
                                'office_id': json.loads((response.content.decode('utf-8')))['id']
                            })
                            temp.is_update = False
                            self.env.cr.commit()
                            export_event.append(json.loads((response.content.decode('utf-8')))['id'])
                            if meeting.recurrency:
                                added.append(meeting.name)

                    elif meeting.is_update:
                        if meeting.office_id:
                            url = "https://graph.microsoft.com/v1.0/me/events/{}".format(meeting.office_id)
                            response = requests.get(
                                url,
                                headers={
                                    'Host': 'outlook.office.com',
                                    'Authorization': 'Bearer {0}'.format(res_user.token),
                                    'Accept': 'application/json',
                                    'X-Target-URL': 'http://outlook.office.com',
                                    'connection': 'keep-Alive'
                                })

                            if response.status_code == 200 or response.status_code == 201:
                                res_event = json.loads((response.content.decode('utf-8')))
                                modified_at = datetime.strptime(
                                    res_event['lastModifiedDateTime'].split(".")[0], '%Y-%m-%dT%H:%M:%S'
                                )

                                if modified_at != meeting.modified_date:
                                    if meeting.modified_date:
                                        if modified_at > meeting.modified_date or modified_at == meeting.modified_date:
                                            continue

                                response = requests.patch(
                                    'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events/' + meeting.office_id,
                                    headers=header, data=json.dumps(payload))
                                if 'id' in json.loads((response.content.decode('utf-8'))):
                                    temp.write({
                                        'office_id': json.loads((response.content.decode('utf-8')))['id']
                                    })
                                    update_event.append(json.loads((response.content.decode('utf-8')))['id'])
                                    meeting.is_update = False
                                    self.env.cr.commit()
                                    if meeting.recurrency:
                                        added.append(meeting.name)

                            else:
                                response = requests.post(
                                    'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events',
                                    headers=header, data=json.dumps(payload))
                                if 'id' in json.loads((response.content.decode('utf-8'))):
                                    temp.write({
                                        'office_id': json.loads((response.content.decode('utf-8')))['id']
                                    })
                                    temp.is_update = False
                                    self.env.cr.commit()
                                    export_event.append(json.loads((response.content.decode('utf-8')))['id'])
                                    if meeting.recurrency:
                                        added.append(meeting.name)

                        else:
                            response = requests.post(
                                'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events',
                                headers=header, data=json.dumps(payload))
                            if 'id' in json.loads((response.content.decode('utf-8'))):
                                temp.write({
                                    'office_id': json.loads((response.content.decode('utf-8')))['id']
                                })
                                temp.is_update = False
                                self.env.cr.commit()
                                export_event.append(json.loads((response.content.decode('utf-8')))['id'])
                                if meeting.recurrency:
                                    added.append(meeting.name)

            export_dictionary = {
            'exportedCalenders': len(export_event),
            'updatedCalenders': len(update_event)
            }

            return export_dictionary

        except Exception as e:
            _logger.error(e)
            raise ValidationError(_(str(e)))

    ''' 
        This following method is responsible for exporting tasks from Odoo
    '''
    def export_tasks(self):
        export_task = []
        update_task = []
        try:
            res_user = self.res_user
            if self.from_date and not self.to_date:
                raise Warning('Please! Select "To Date" to Import Events.')
            if self.from_date and self.to_date:
                from_date = self.from_date
                to_date = self.to_date

            odoo_activities = self.env['mail.activity'].search([('user_id', '=', self.res_user.id)])
            if self.from_date and self.to_date:
                odoo_activities = odoo_activities.search(
                    [('write_date', '>=', self.from_date), ('write_date', '<=', self.to_date)])

            url = 'https://graph.microsoft.com/v1.0/me/todo/lists/tasks'

            response = requests.get(
                url,
                headers={
                    'Authorization': 'Bearer {0}'.format(res_user.token),
                    'Content-type': 'application/json',
                    'connection': 'keep-Alive'
                })
            res_data = json.loads((response.content.decode('utf-8')))

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
                            })
                        res_task = json.loads((response.content.decode('utf-8')))
                        if 'id' not in res_task.keys():
                            # raise osv.except_osv(
                            #     ("Access Token Expired!"),
                            #     (" Please Regenerate Access Token !")
                            # )
                            raise UserError(_
                                ("Access Token Expired!\nPlease Regenerate Access Token !"))
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
                        })

                    if 'id' not in json.loads((response.content.decode('utf-8'))).keys():
                        # raise osv.except_osv(_("Error!"), (_(response["error"])))
                        raise UserError(_("Error! " + str(response["error"])))
                    activity.office_id = json.loads((response.content.decode('utf-8')))['id']
                    export_task.append(activity.office_id)
                    activity.is_update = False
                self.env.cr.commit()

            export_dictionary = {
                'exportedTasks': len(export_task),
                'updatedTasks': len(update_task)
                }

            return export_dictionary

        except Exception as e:
            _logger.error(e)
            raise ValidationError(_(str(e)))

    ''' 
        This following method is responsible for exporting contacts from Odoo
    '''
    def export_contacts(self):
        new_contact = []
        update_contact = []
        try:
            res_user = self.res_user
            if self.from_date and not self.to_date:
                raise Warning('Please! Select "To Date" to Import Events.')
            if self.from_date and self.to_date:
                from_date = self.from_date
                to_date = self.to_date

            odoo_contacts = self.env['res.partner'].search([("create_uid", '=', res_user.id)])

            if self.from_date and self.to_date:
                odoo_contacts = odoo_contacts.search(
                    [('write_date', '>=', self.from_date), ('write_date', '<=', self.to_date),
                     ('is_update', '=', True)])

            headers = {
                'Host': 'outlook.office365.com',
                'Authorization': 'Bearer {0}'.format(res_user.token),
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'connection': 'keep-Alive'
            }

            for contact in odoo_contacts:

                data = {
                    'displayName': contact.name if contact.is_company == False else None,
                    'givenName': contact.firstName if contact.firstName else None,
                    'surname': contact.lastName if contact.lastName else None,
                    'companyName': contact.company_name if contact.is_company == False and contact.company_name == True else contact.name if contact.is_company == True else None,
                    'jobTitle': contact.function if contact.function else None,
                    'businessPhones': [
                        contact.phone if contact.phone else None
                    ],
                    'mobilePhone': contact.mobile if contact.mobile else None,
                    'businessHomePage': contact.website if contact.website else None,
                }
                if contact.email:
                    data["emailAddresses"] = [
                        {
                            "address": contact.email if contact.email else None,
                        },
                    ]

                data["businessAddress"] = {
                    "street": contact.street if contact.street else (
                        contact.street2 if contact.street2 else None),
                    "city": contact.city if contact.city else None,
                    "state": contact.state_id.name if contact.state_id else None,
                    "countryOrRegion": contact.country_id.name if contact.country_id else None,
                    "postalCode": contact.zip if contact.zip else None
                }

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
                        })
                    
                    if response.status_code == 200 or response.status_code == 201 :
                            if contact.create_date < contact.write_date:
                                res_event = json.loads((response.content.decode('utf-8')))
                                modified_at = datetime.strptime(res_event['lastModifiedDateTime'][:-1], '%Y-%m-%dT%H:%M:%S')
                                if modified_at > contact.write_date or modified_at == contact.write_date:
                                    pass
                                else:
                                    update_response = requests.patch(
                                        'https://graph.microsoft.com/v1.0/me/contacts/' + str(
                                            contact.office_contact_id), data=json.dumps(data), headers=headers
                                    )
                                    if update_response.status_code == 200 or update_response.status_code == 201:
                                        update_response = json.loads(update_response.content.decode('utf-8')) 
                                        contact.write({'office_contact_id': update_response['id']})
                                        update_contact.append(update_response['id'])
                                    contact.is_update = False
                    else:
                        post_response = requests.post(
                            'https://graph.microsoft.com/v1.0/me/contacts', data=json.dumps(data),
                            headers=headers
                        )

                        if post_response.status_code == 200 or post_response.status_code == 201:
                            post_response = json.loads(post_response.content.decode('utf-8'))
                            contact.write({'office_contact_id': post_response['id']})
                            contact.is_update = False
                            new_contact.append(post_response['id'])

                else:
                    post_response = requests.post(
                        'https://graph.microsoft.com/v1.0/me/contacts', data=json.dumps(data),
                        headers=headers
                    )

                    if post_response.status_code == 200 or post_response.status_code == 201:
                        post_response = json.loads(post_response.content.decode('utf-8'))
                        contact.write({'office_contact_id': post_response['id']})
                        contact.is_update = False
                        new_contact.append(post_response['id'])

            export_dictionary = {
            'exportedContacts': len(new_contact),
            'updatedContacts': len(update_contact)
            }

            return export_dictionary

        except Exception as e:
            raise ValidationError(_(str(e)))