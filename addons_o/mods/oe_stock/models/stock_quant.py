# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import config, float_compare

class StockQuantHistory(models.Model):
    _name = "stock.quant.history"
    _description = "Stock quant history"
    _order = "create_date desc"
    
    quant_id = fields.Many2one('stock.quant', string="Quant")
    qty = fields.Float(string='Quantity')
    royal_qty = fields.Float(string='Quantity')
    product_id = fields.Many2one('product.template', string='Product', required=True)
    name = fields.Text(string='Description', size=250)
    create_date = fields.Datetime('Create Date', readonly=True)
    write_date = fields.Datetime('Update Date', readonly=True)
    location_id = fields.Many2one('stock.location', 'Location',)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    
    quant_history_ids = fields.One2many('stock.quant.history', 'quant_id', string='History of physical products')


    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        """ Return the available quantity, i.e. the sum of `quantity` minus the sum of
        `reserved_quantity`, for the set of quants sharing the combination of `product_id,
        location_id` if `strict` is set to False or sharing the *exact same characteristics*
        otherwise.
        This method is called in the following usecases:
            - when a stock move checks its availability
            - when a stock move actually assign
            - when editing a move line, to check if the new value is forced or not
            - when validating a move line with some forced values and have to potentially unlink an
              equivalent move line in another picking
        In the two first usecases, `strict` should be set to `False`, as we don't know what exact
        quants we'll reserve, and the characteristics are meaningless in this context.
        In the last ones, `strict` should be set to `True`, as we work on a specific set of
        characteristics.

        :return: available quantity as a float
        """
        self = self.sudo()
        force = self._context.get('force', True)
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        rounding = product_id.uom_id.rounding
        if product_id.tracking == 'none':
            available_quantity = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if force and available_quantity <= 0.0:
                available_quantity = sum(quants.mapped('quantity'))
            if allow_negative:
                return available_quantity
            else:
                return available_quantity if float_compare(available_quantity, 0.0, precision_rounding=rounding) >= 0.0 else 0.0
        else:
            availaible_quantities = {lot_id: 0.0 for lot_id in list(set(quants.mapped('lot_id'))) + ['untracked']}
            for quant in quants:
                if not quant.lot_id:
                    availaible_quantities['untracked'] += quant.quantity - quant.reserved_quantity
                else:
                    availaible_quantities[quant.lot_id] += quant.quantity - quant.reserved_quantity
            if allow_negative:
                return sum(availaible_quantities.values())
            else:
                return sum([available_quantity for available_quantity in availaible_quantities.values() if float_compare(available_quantity, 0, precision_rounding=rounding) > 0])


    @api.multi
    @api.constrains('product_id', 'quantity')
    def check_negative_qty(self):
        p = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        check_negative_qty = (
            (config['test_enable'] and
             self.env.context.get('test_stock_no_negative')) or
            not config['test_enable']
        )
        #check_negative_qty = False
        if not check_negative_qty:
            return

        for quant in self:
            disallowed_by_product = \
                not quant.product_id.allow_negative_stock \
                and not quant.product_id.categ_id.allow_negative_stock
            disallowed_by_location = not quant.location_id.allow_negative_stock
            if (
                float_compare(quant.quantity, 0, precision_digits=p) == -1 and
                quant.product_id.type == 'product' and
                quant.location_id.usage in ['internal', 'transit'] and
                disallowed_by_product and disallowed_by_location
            ):
                msg_add = ''
                if quant.lot_id:
                    # Now find a quant we can compensate the negative quants
                    #  with some untracked quants.
                    untracked_qty = quant._get_available_quantity(
                        quant.product_id, quant.location_id, lot_id=False,
                        strict=True)
                    if float_compare(abs(quant.quantity),
                                     untracked_qty, precision_digits=p) < 1:
                        return True
                    msg_add = _(" lot '%s'") % quant.lot_id.display_name
                raise ValidationError(_(
                    "You cannot validate this stock operation because the "
                    "stock level of the product '%s'%s would become negative "
                    "(%s) on the stock location '%s' and negative stock is "
                    "not allowed for this product and/or location.") % (
                        quant.product_id.name, msg_add, quant.quantity,
                        quant.location_id.complete_name))
