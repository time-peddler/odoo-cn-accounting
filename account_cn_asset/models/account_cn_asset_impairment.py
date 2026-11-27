# -*- coding: utf-8 -*-
from odoo import Command, _, fields, models
from odoo.exceptions import UserError


class AccountCnAssetImpairment(models.Model):
    _name = 'account.cn.asset.impairment'
    _description = '固定资产减值记录'
    _order = 'date desc, id desc'

    asset_id = fields.Many2one(
        comodel_name='account.cn.asset', string='资产', required=True, ondelete='cascade',
    )
    currency_id = fields.Many2one(related='asset_id.currency_id', string='币种')
    date = fields.Date(string='减值日期', required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='减值金额', required=True, currency_field='currency_id')
    reason = fields.Char(string='减值原因')
    move_id = fields.Many2one(comodel_name='account.move', string='减值凭证', readonly=True, copy=False)
    state = fields.Selection(
        selection=[('draft', '草稿'), ('posted', '已过账')],
        string='状态', default='draft', required=True, copy=False,
    )

    def action_post(self):
        for impairment in self:
            if impairment.state == 'posted':
                continue
            asset = impairment.asset_id
            category = asset.category_id
            Account = self.env['account.account']
            loss_account = Account.search([
                ('company_ids', 'in', asset.company_id.id),
                ('code', '=', '6701'),
            ], limit=1)
            if not loss_account:
                raise UserError(_('未找到"资产减值损失"科目（编码 6701），请先在科目表中补充该科目。'))
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': category.journal_id.id,
                'company_id': asset.company_id.id,
                'date': impairment.date,
                'ref': _('%s：计提减值') % asset.name,
                'line_ids': [
                    Command.create({
                        'account_id': loss_account.id,
                        'debit': impairment.amount,
                        'credit': 0.0,
                        'name': _('资产减值损失'),
                    }),
                    Command.create({
                        'account_id': category.impairment_account_id.id,
                        'debit': 0.0,
                        'credit': impairment.amount,
                        'name': _('固定资产减值准备'),
                    }),
                ],
            })
            move.action_post()
            impairment.write({'move_id': move.id, 'state': 'posted'})
