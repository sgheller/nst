# -*- coding: utf-8 -*-

from odoo import models, api, fields


class MailTemplate(models.Model):
    _inherit = "mail.template"

    send_product_attachments = fields.Boolean("Send Products attachments", default=False)


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        r = super(MailComposeMessage, self).onchange_template_id(template_id, composition_mode, model, res_id)
        template = self.env['mail.template'].browse(template_id)
        if template.send_product_attachments:
            product_attachments = self.get_product_attachments(template, res_id)
            if len(product_attachments):
                if not r['value'].get('attachment_ids'):
                    r['value']['attachment_ids'] = [(6, 0, product_attachments.ids)]
                else:
                    r['value']['attachment_ids'] = [(6, 0, r['value']['attachment_ids'][0][2] + product_attachments.ids)]
        return r

    @api.model
    def get_product_attachments(self, template, res_id):
        order = self.env[template.model].browse(res_id)
        products = order.mapped('order_line.product_id')
        attachments = self.env['ir.attachment'].search(
            [
                '|', '&',
                ('res_model', 'in', ['product.product']),
                ('res_id', 'in', products.ids),'&',('res_model', 'in', ['product.template']),
                ('res_id', 'in', products.mapped('product_tmpl_id').ids)
            ])
        return attachments
