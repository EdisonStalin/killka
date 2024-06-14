# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import RedirectWarning

class ProductCombo(models.Model):
    _name = "product.combo"
    _description = "Product packs"

    @api.multi
    @api.onchange('product_id')
    def product_id_onchange(self):
        return {'domain': {'product_id': [('is_combo', '=', False)]}}

    name = fields.Char(string='name')
    product_template_id = fields.Many2one('product.template', string='Item')
    product_quantity = fields.Float('Quantity', default=1, required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    uom_id = fields.Many2one('product.uom', related='product_id.uom_id')
    price = fields.Float(string='Product price')


class ProductPriceHistory(models.Model):
    """ Keep track of the ``product.template`` standard prices as they are changed. """
    _inherit = 'product.price.history'


    product_tmpl_id = fields.Many2one('product.template', string='Product', ondelete='cascade')

    
    @api.model
    def create(self, vals):
        product_id = self.env['product.product'].browse(vals['product_id'])
        vals['product_tmpl_id'] = product_id.product_tmpl_id.id
        return super(ProductPriceHistory, self).create(vals)


class ProductTemplate(models.Model):
    _inherit = 'product.template'


    @api.multi
    def _get_default_category_id(self):
        context = self._context or {}
        if context.get('categ_id'):
            return context.get('categ_id') or context.get('default_categ_id')
        category = self.env['product.category'].search([('active', '=', True)], limit=1)
        if category:
            return category.id
        else:
            err_msg = _('You must define at least one product category in order to be able to create products.')
            redir_msg = _('Go to Internal Categories')
            raise RedirectWarning(err_msg, self.env.ref('product.product_category_action_form').id, redir_msg)


    @api.depends('history_price_ids')
    def _compute_standard_price(self):
        super(ProductTemplate, self)._compute_standard_price()
        for product_id in self:
            product_id.last_cost = product_id.get_history_price(self.env.user.company_id.id)

    
    name = fields.Char('Name', index=True, required=True, translate=False)
    last_cost = fields.Float(compute='_compute_standard_price', store=True, digits=dp.get_precision('Product Price'), help='Current Last Cost')
    sheet_product_id = fields.Binary('file', attachment=True)
    filename_product = fields.Char('Filename', size=250)
    template_id = fields.Many2one('mail.template', 'Use template', index=True)
    categ_id = fields.Many2one('product.category', string='Internal Category',
        change_default=True, default=_get_default_category_id,
        required=True, help="Select category for the current product")
    is_combo = fields.Boolean(string='Combo Product', default=False, help='Enable the option for the product to display a list')
    combo_product_ids = fields.One2many('product.combo', 'product_template_id', string='Combo Item')
    history_price_ids = fields.One2many('product.price.history', 'product_tmpl_id', string='Price History')


    def get_history_price(self, company_id, date=None):
        domain = [
            ('company_id', '=', company_id),
            ('product_id', 'in', self.ids),
            ('datetime', '<=', date or fields.Datetime.now())]
        history = self.env['product.price.history'].search(domain, order='datetime desc,id desc', limit=1)
        return history.cost or 0.0


class ProductProduct(models.Model):
    _inherit = 'product.product'


    @api.depends('history_price_ids')
    def _get_last_cost(self):
        for product_id in self:
            product_id.last_cost = product_id.get_history_price(self.env.user.company_id.id)


    last_cost = fields.Float(compute='_get_last_cost', store=True, digits=dp.get_precision('Product Price'), help='Current Last Cost' )
    history_price_ids = fields.One2many('product.price.history', 'product_id', string='Price History')


    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('default_warehouse_id'):
            warehouse_id = self.env['stock.warehouse'].browse(context.get('default_warehouse_id'))
            domain = [('location_id','=',warehouse_id.lot_stock_id.id),('company_id','=',self.env.user.company_id.id)]
            product_ids = self.env['stock.quant'].search(domain).mapped('product_id')
            if len(product_ids):
                args += [('id', 'in', product_ids.ids)]
        return super(ProductProduct, self).search(args, offset, limit, order='sequence desc', count=count)


    def get_history_price(self, company_id, date=None):
        domain = [
            ('company_id', '=', company_id),
            ('product_id', 'in', self.ids),
            ('datetime', '<=', date or fields.Datetime.now())]
        history = self.env['product.price.history'].search(domain, order='datetime desc,id desc', limit=1)
        return history.cost or 0.0

    