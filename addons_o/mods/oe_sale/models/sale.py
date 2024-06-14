# -*- coding: utf-8 -*-

from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _amount_all(self):
        super(SaleOrder, self)._amount_all()
        for order in self:
            amount_discount = 0.0
            for line in order.order_line:
                amount_discount = line.discount if line.type_discount=='fixed' else ((line.product_uom_qty * line.price_unit) * line.discount) /100.0
            order.amount_discount = amount_discount
    
    #template_simple_id = fields.Many2one('template.simple', string='Use template', index=True)
    amount_discount = fields.Monetary(string='Discount Amount', store=True, compute='_amount_all', track_visibility='onchange')
    print_image = fields.Boolean(string='Print Image', copy=True, help="""If ticked, you can see the product image in report of sale order/quotation""")
    establishment_id = fields.Many2one('res.establishment', string='Business Store', readonly=True,
        states={'draft': [('readonly', False)]}, track_visibility='always', copy=True)
    vendor_id = fields.Many2one('res.partner', string='Sale Vendor',
        states={'draft': [('readonly', False)]}, track_visibility='always',
        change_default=True, default=lambda self: self.env.user.partner_id, copy=True)
    
    
    #@api.onchange('template_simple_id')
    #def _onchange_template_simple(self):
    #    self.ensure_one()
    #    if self.template_simple_id:
    #        self.note = self.template_simple_id.body


    def _get_default_sms_recipients(self):
        """ Method overriden from mail.thread (defined in the sms module).
            SMS text messages will be sent to attendees that haven't declined the event(s).
        """
        return self.mapped('partner_id')


    @api.multi
    def _get_exists_signature(self):
        self.ensure_one()
        signature = self.env['ir.attachment'].search([('res_name', '=', self.name), ('res_id', '=', self.id), ('mimetype', '=', 'image/png')])
        return signature or False


    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        res = super(SaleOrder, self).action_invoice_create(grouped, final)
        obj_invoice = self.env['account.invoice']
        for x in res:
            invoice = obj_invoice.browse(x)
            vals = invoice.authorization_id._get_info_authorization()
            invoice.write({'line_info_ids': vals})
        return res


    @api.multi
    def _get_signature(self):
        self.ensure_one()
        signature = self._get_exists_signature()
        return signature.datas
    
    
    @api.multi
    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            templates = []
            for line in self.order_line:
                if line.product_id.template_id: templates.append(line.product_id.template_id.id)
            template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1] if len(templates)== 0 else templates[0]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "sale.mail_template_data_notification_email_sale_order",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


    @api.multi
    def action_update(self):
        for line in self.order_line:
            line._compute_invoice_status()
        self._amount_all()

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    image_small = fields.Binary(related='product_id.image_small', string='Product Image')
    type_discount = fields.Selection(default='percent', required=True, selection=[('fixed', 'Fixed'), ('percent', 'Percentage')])

