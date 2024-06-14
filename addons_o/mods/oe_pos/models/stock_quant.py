# -*- coding: utf-8 -*-

from odoo import models, api
from collections import deque

class StockQuantity(models.Model):
    _inherit = 'stock.quant'


    @api.model
    def get_qty_available(self, location_id, location_ids=None, product_ids=None):
        if location_id:
            root_location = self.env['stock.location'].search([('id', '=', location_id)])
            all_location = [root_location.id]
            queue = deque([])
            self.location_traversal(queue, all_location, root_location)
            stock_quant = self.search_read([('location_id', 'in', all_location)], ['product_id', 'quantity', 'location_id'])
            return stock_quant
        else:
            stock_quant = self.search_read([('location_id', 'in', location_ids), ('product_id', 'in', product_ids)],
                                           ['product_id', 'quantity', 'location_id'])
            return stock_quant


    def location_traversal(self, queue, res, root):
        for child in root.child_ids:
            if child.usage == 'internal':
                queue.append(child)
                res.append(child.id)
        while queue:
            pick = queue.popleft()
            res.append(pick.id)
            self.location_traversal(queue, res, pick)


    @api.model
    def create(self, vals):
        res = super(StockQuantity, self).create(vals)
        if res.location_id.usage == 'internal':
            self.env['pos.stock.channel'].broadcast(res)
        return res


    @api.multi
    def write(self, vals):
        record = self.filtered(lambda x: x.location_id.usage == 'internal')
        self.env['pos.stock.channel'].broadcast(record)
        return super(StockQuantity, self).write(vals)
