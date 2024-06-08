# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.osv import expression


class AccountJournalValues(models.Model):
    _name = "account.journal.values"
    _description = "Extra payment values"
    
    
    name = fields.Char(string='Reference', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    type = fields.Selection(default='percent', required=True, selection=[('amount', 'Amount Fixed'), ('percent', 'Percentage')])
    amount = fields.Float(string='Value', digits=(16,4), default=0.0, help='Referred value to calculate in the payment.')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    establishment_id = fields.Many2one('res.establishment', string='Business Store')
    authorization_id = fields.Many2one('account.authorization', string='Authorization')
    method_id = fields.Many2one('account.method.payment', string='Payment Method', help='Choose the form of payment made by the client')
    card_type_id = fields.Many2one('account.card.type', string='Card Type', help='Choose the form of card type by the client')
    show_details = fields.Boolean(string='Show Details', help='Allows you to show details of the pending values ​​that you can add to the payment.')
    is_card = fields.Boolean(string='Is Card?', help='It will enable extra values ​​that will be added to the payment.')
    line_values_ids = fields.One2many('account.journal.values', 'journal_id', string='Extra Values', copy=False)


    @api.model
    def default_get(self, default_fields):
        res = super(AccountJournal, self).default_get(default_fields)
        res['update_posted'] = True
        return res


    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            args = args or []
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            return self.search(expression.AND([domain, args]), limit=limit).name_get()
        return super(AccountJournal, self).name_search(name=name, args=args, operator=operator, limit=limit)