# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleRequisitionGenerate(models.TransientModel):
    _name = 'purchase_requisition.requisition.generate'
    _description = 'Generate Requisition From Sale Order'

    product_ids = fields.Many2many('product.product')

    @api.model
    def default_get(self, fields):
        res = super(SaleRequisitionGenerate, self).default_get(fields)
        res_ids = self._context.get('active_ids')

        products = self.env['product.product']
        sale_order = self.env["sale.order"].browse(res_ids)
        products_all = self._get_products(sale_order)
        for product_id, quantity in products_all.items():
            if product_id.purchase_ok and product_id.seller_ids:
                products |= product_id

        res['product_ids'] = [(6, 0, products.ids)]
        return res

    def _get_products(self, order_id):
        lines = {}
        for line in order_id.order_line:
            if line.product_id in lines:
                lines[line.product_id] += line.product_uom_qty
            else:
                lines[line.product_id] = line.product_uom_qty
            if line.product_id.bom_count:
                boms = self.env['mrp.bom'].search(['|', ('product_id', '=', line.product_id.id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)])
                for bom in boms:
                    components = self.env['report.mrp.report_bom_structure']._get_pdf_line(bom.id, line.product_id, line.product_uom_qty, child_bom_ids=[], unfolded=True)
                    if components.get('lines'):
                        for component in components['lines']:
                            product_component = self.env['product.product'].browse(component['prod_id'])
                            if product_component in lines:
                                lines[product_component] += line.product_uom_qty
                            else:
                                lines[product_component] = line.product_uom_qty

        return lines

    def generate(self):
        res_ids = self._context.get('active_ids')
        sale_order = self.env["sale.order"].browse(res_ids)
        products_all = self._get_products(sale_order)
        for record in self:
            # create requisition
            if len(record.product_ids):
                purchase_vals = {
                    'type_id': self.env.ref('purchase_requisition.type_multi').id,
                    'company_id': self.env.company.id,
                    'currency_id': self.env.company.currency_id.id,
                    'origin': sale_order.name,
                    'sale_id': sale_order.id,
                }
                requisition = self.env["purchase.requisition"].create(purchase_vals)
            for product in record.product_ids:
                if products_all.get(product):
                    qty = products_all[product]
                else:
                    qty = 1
                line_vals = {
                    'product_id': product.id,
                    'product_qty': qty,
                    'product_uom_id': product.uom_po_id.id,
                    'requisition_id': requisition.id,
                }
                self.env["purchase.requisition.line"].create(line_vals)
            requisition.action_in_progress()
            requisition.generate_default_purchase_orders()






