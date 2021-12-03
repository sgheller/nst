# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    sale_id = fields.Many2one('sale.order', 'Sale Order')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Compte Analytique')
    partner_ids = fields.Many2many('res.partner', string='Vendors', help="List of partners that will be added as follower of the current document.",
                                   domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    generate_all_lines = fields.Boolean(string="Generate All Lines", default=False)
    generate_all_lines_display = fields.Boolean(compute="_compute_generate_all_lines_display")
    purchase_ids = fields.One2many('purchase.order', 'requisition_id', string='Purchase Orders', domain="[('state', '!=', 'cancel')]",
                                   states={'done': [('readonly', True)]})

    @api.onchange('partner_ids')
    def _compute_generate_all_lines_display(self):
        for req in self:
            req.generate_all_lines_display = len(req.partner_ids) != 0

    def purchase_requisition_add_products(self):
        compose_form = self.env.ref('phi_requisition_from_sale_order.view_purchase_requisition_add_products', raise_if_not_found=False)

        return {
            'name': _('Add Products'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.requisition.add.products',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
        }

    def generate_default_purchase_orders(self):
        self.ensure_one()
        for line in self.line_ids:
            if len(self.partner_ids):
                if self.generate_all_lines:
                    vendors = self.partner_ids
                else:
                    vendors = self.partner_ids.filtered(lambda p: p.id in line.product_id.seller_ids.mapped('name').ids)
            else:
                vendors = line.product_id.seller_ids.mapped('name')
            for vendor in vendors:
                purchase_order = self.purchase_ids.filtered(lambda s: s.partner_id == vendor)
                if not purchase_order:
                    purchase_order = self.env['purchase.order'].create({
                        'partner_id': vendor.id,
                        'requisition_id': self.id,
                        'date_order': self.ordering_date or self.write_date,
                        'account_analytic_id': self.account_analytic_id.id,
                    })
                seller = line.product_id._select_seller(partner_id=vendor, quantity=line.product_qty, uom_id=line.product_uom_id)
                self.env['purchase.order.line'].create({
                    'order_id': purchase_order.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom': line.product_uom_id.id,
                    'date_planned': line.schedule_date or self.schedule_date or purchase_order.date_order,
                    'price_unit': seller.price if seller else 0,
                })

    def action_comparison(self):
        action = self.env.ref('phi_requisition_from_sale_order.action_requisition_purchase_order_line').read()[0]
        return action

    def action_done(self):
        self.purchase_ids.order_line.filtered(lambda l: not l.requisition_selected).unlink()
        self.purchase_ids.filtered(lambda o: o.state in ('draft', 'send') and not len(o.order_line)).button_cancel()
        self.purchase_ids.filtered(lambda o: o.state in ('draft', 'send')).button_confirm()
        self.line_ids.filtered(lambda l: not l.qty_ordered).unlink()
        super(PurchaseRequisition, self).action_done()

    def cancel_update_cost(self):
        for order in self.purchase_ids.filtered(lambda o: o.state in ('draft', 'send')):
            order._add_supplier_to_product()
        super(PurchaseRequisition, self).action_cancel()


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    requisition_selected = fields.Boolean(string="Selected", compute="_compute_requisition_selected")
    purchase_order_line_ids = fields.One2many('purchase.order.line', compute="compute_purchase_order_line_ids")
    partner_selected_ids = fields.Many2many("res.partner", string="Vendor", compute="_compute_partner_ids")
    no_vendors = fields.Boolean(string="No Vendor", compute="_compute_no_vendors")

    def _compute_no_vendors(self):
        for line in self:
            line.no_vendors = len(line.purchase_order_line_ids) == 0

    def _compute_requisition_selected(self):
        for line in self:
            line.requisition_selected = any(ol.requisition_selected for ol in line.purchase_order_line_ids)

    def compute_purchase_order_line_ids(self):
        for line in self:
            purchase_order_lines = self.env['purchase.order.line'].search([('requisition_id', '=', line.requisition_id.id), ('product_id', '=', line.product_id.id), ('state', '!=', 'cancel')])
            line.purchase_order_line_ids = [(6, False, purchase_order_lines.ids)]

    def _compute_partner_ids(self):
        for line in self:
            partner_ids = line.purchase_order_line_ids.filtered(lambda order_line: order_line.requisition_selected).order_id.mapped('partner_id')
            line.partner_selected_ids = [(6, False, partner_ids.ids)]

    @api.onchange('requisition_selected')
    def _on_change_requisition_selected(self):
        for line in self:
            pass

    @api.depends('requisition_id.purchase_ids.state', 'requisition_id.purchase_ids.order_line.requisition_selected',
                 'requisition_id.purchase_ids.order_line.price_unit',
                 'requisition_id.purchase_ids.order_line.product_qty',
                 'requisition_id.purchase_ids.order_line.date_planned')
    def _compute_ordered_qty(self):
        line_found = set()
        for line in self:
            total = 0.0
            price = 0.0
            schedule_date = False
            po_lines = []
            for po in line.requisition_id.purchase_ids:
                if po.state in ('purchase', 'done'):
                    po_lines = po.order_line.filtered(lambda order_line: order_line.product_id == line.product_id)
                elif po.state in ('draft', 'sent'):
                    po_lines = po.order_line.filtered(lambda order_line: order_line.product_id == line.product_id and order_line.requisition_selected)
                if len(po_lines):
                    for po_line in po_lines:
                        if po_line.product_uom != line.product_uom_id:
                            total += po_line.product_uom._compute_quantity(po_line.product_qty, line.product_uom_id)
                        else:
                            total += po_line.product_qty
                        price = po_line.price_unit
                        schedule_date = po_line.date_planned
            if line.product_id not in line_found:
                line.qty_ordered = total
                line.price_unit = price
                line.schedule_date = schedule_date
                line_found.add(line.product_id)
            else:
                line.qty_ordered = 0
                line.price_unit = 0
                line.schedule_date = False

    def action_comparison_line(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("phi_requisition_from_sale_order.action_requisition_purchase_order_line")
        action['res_id'] = self.requisition_id.id
        action['context'] = {"default_requisition_id": self.requisition_id.id}
        action['domain'] = [('requisition_id', '=', self.requisition_id.id), ('product_id', '=', self.product_id.id)]
        return action
