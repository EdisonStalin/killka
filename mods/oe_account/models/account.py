# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError


class AccountAccountType(models.Model):
    _inherit = 'account.account.type'
    
    active = fields.Boolean(default=True, help="Set active to false to hide the account type without removing it.")


class AccountAccount(models.Model):
    _inherit = 'account.account'
    
    parent_id = fields.Many2one('account.account', string='Father Account')
    child_ids = fields.One2many('account.account', 'parent_id', string='Father Account')
    level = fields.Integer(u'Level', compute='_compute_level', store=True)
    movement = fields.Selection(selection=[('account','Account'), ('subaccount', 'Subaccount')],
        string='Movement', default='account', required=True, copy=True)


    @api.depends('parent_id')
    def _compute_level(self):
        for acc in self:
            level = 1
            cur = acc
            while cur.parent_id:
                level += 1
                cur = cur.parent_id
            acc.level = level

    @api.model
    def create(self, vals):
        res = super(AccountAccount, self).create(vals)
        if not res.parent_id:
            parent = self._set_account_hierarchy(res.id)
            res.parent_id = parent.id if parent else False
            if not len(res.child_ids):
                res.movement = 'subaccount'
        return res


    @api.multi
    def write(self, vals):
        # Dont allow changing the company_id when account_move_line already exist
        if vals.get('company_id', False):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            for account in self:
                if (account.company_id.id != vals['company_id']) and move_lines:
                    raise UserError(_('You cannot change the owner company of an account that already contains journal items.'))
        for account in self:
            if 'parent_id' not in vals:
                parent = account._set_account_hierarchy(account.id)
                vals['parent_id'] = parent.id if parent else False
            if vals.get('currency_id'):
                if self.env['account.move.line'].search_count([('account_id', '=', account.id), ('currency_id', 'not in', (False, vals['currency_id']))]):
                    raise UserError(_('You cannot set a currency on this account as it already has some journal entries having a different foreign currency.'))
        return models.Model.write(self, vals)


    @api.multi
    def action_check_hierarchy(self):
        accounts = self.search([('id', 'in', self.ids), ('company_id', '=', self.env.user.company_id.id)], order="id desc")
        for account in self.web_progress_iter(accounts, _('reviewing record') + "({})".format(self._description)):
            parent = self._set_account_hierarchy(account.id)
            account.parent_id = parent.id if parent else False
            if not len(account.child_ids):
                account.movement = 'subaccount'

    def _set_account_hierarchy(self, account=None):
        acc = self.browse(account)
        acc.parent_id = False
        company_id = self.env.user.company_id
        parent = False
        for sep in ['.', '-', ';', ',']:
            if sep in acc.code:
                seppos = (acc.code[-1] == sep and acc.code[:-1].rfind(sep) > - 1 and acc.code[: - 1].rfind(sep)) or acc.code.rfind(sep)
                parent = self.search([('id', '!=', acc.id), ('company_id', '=', company_id.id), ('code', '=', acc.code[:seppos + 1])], limit=1)
                if not acc.parent_id.id:
                    parent = self.search([('id', '!=', acc.id), ('company_id', '=', company_id.id), ('code', '=', acc.code[:seppos])], limit=1)
                break
        if not acc.parent_id.id:
            for y in range(len(acc.code) - 1):
                domain = [('id', '!=', acc.id), ('company_id', '=', company_id.id), ('code', 'in', [acc.code[:-(y + 1)] + '' * z for z in range(y + 2)])]
                parent = self.search(domain, limit=1)
                if parent.id:
                    break
        return parent

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('child'):
            args += [('movement','=','subaccount')]
        return super(AccountAccount, self).search(args, offset, limit=limit, order=order, count=count)
