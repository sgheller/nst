# -*- coding: utf-8 -*-
from datetime import datetime
import werkzeug
import werkzeug.utils
from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
import time


class Office365Code(http.Controller):
    @http.route("/odoo", auth="public", type='http')
    def fetch_code(self, **kwargs):
        odoo_user = request.env['res.users'].sudo().browse(int(request.env.user.id))
        if "error" in kwargs:
            ValidationError(kwargs['error'])
        user_setting = request.env['res.config.settings']
        if 'code' in kwargs:
            code = kwargs.get('code')
            response = user_setting.generate_token(code)
            if 'token' in response:
                odoo_user.sudo().update({
                    'token': response['token'],
                    'refresh_token': response['refresh_token'],
                    'expires_in': int(round(time.time() * 1000)),
                    'code': code,
                })
                request.env.cr.commit()
                return request.render("odoo_office365.token_redirect_success_page")
            else:
                return request.render("odoo_office365.token_redirect_fail_page")
        else:
            return request.render("odoo_office365.token_redirect_fail_page")