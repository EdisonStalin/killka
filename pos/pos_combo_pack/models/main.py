from odoo import api, fields, models


class PosOrderLineCombo(models.Model):
    _name = "pos.order.line.combo"
    
    qty = fields.Float('Quantity', default='1', required=True)
    product_id = fields.Many2one('product.product', 'Item')
    line_id = fields.Many2one('pos.order.line', 'POS Line')


    @api.model
    def create(self, vals):
        if 'name' in vals:
            del vals['name']
        if 'tax_ids' in vals:
            del vals['tax_ids']
        return super(PosOrderLineCombo, self).create(vals)


class ProductPack(models.Model):
    _name = "product.pack"
    _description = "Product packs"


    product_categ_id = fields.Many2one('pos.category', string='Category', required=True)
    product_quantity = fields.Float(string='Quantity', default='1', required=True)
    product_template_id = fields.Many2one('product.template', string='Item')
    default_product_id = fields.Many2one('product.template', string='Default Item')
    is_extra = fields.Boolean(string='Is Extra', help='Product is extra inside the combo')


    @api.onchange('product_categ_id', 'default_product_id')
    def _onchange_default_product_id(self):
        res = {'domain': {}}
        if self.product_categ_id:
            product_ids = self.env['product.template'].search([('available_in_pos', '=', True), 
                                                 ('pos_categ_id', '=', self.product_categ_id.id)])
            res['domain']['default_product_id'] = [('id', 'in', product_ids.ids)]
        return res


class FixProductPack(models.Model):
    _name = "fix.product.pack"


    product_p_id = fields.Many2one('product.product', string='Product', required=True)
    product_quantity = fields.Float('Quantity', default='1', required=True)
    product_template_id = fields.Many2one('product.template', 'Item')



class pos_order_line_own(models.Model):
    _name = "pos.order.line.own"
    qty = fields.Float('Quantity', default='1', required=True)
    product_id = fields.Many2one('product.product', 'Item')
    orderline_id = fields.Many2one('pos.order.line', 'POS Line')
    price  = fields.Float('Price',required=True)


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"
    
    is_pack = fields.Boolean("Is Combo Pack")
    combo_ids = fields.One2many("pos.order.line.combo", 'line_id', "Combo Line")
    is_extra = fields.Boolean("Is Extra")
    own_ids = fields.One2many("pos.order.line.own", 'orderline_id', "Extra Toppings")


    @api.model
    def create(self, vals):
        if 'line_id' in vals:
            del vals['line_id']
        return super(PosOrderLine, self).create(vals)

    
class ProductExtraTopping(models.Model):
    _name = "product.extra.topping"
    _rec_name = 'product_categ_id'

    product_template_id = fields.Many2one('product.template', 'Item')
    multi_selection = fields.Boolean("Multiple Selection")
    product_categ_id = fields.Many2one('pos.category', 'Category', required=True)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_pack = fields.Boolean('Combo Pack', default=False)
    is_extra = fields.Boolean('Make Own', default=False,help="This will use for ")
    product_extra_id = fields.One2many('product.extra.topping', 'product_template_id', 'Product Toppings')
    product_pack_id = fields.One2many('product.pack', 'product_template_id', 'Items in the pack')
    product_fix_pro_ids = fields.One2many('fix.product.pack','product_template_id', 'Fix Pack Product')
