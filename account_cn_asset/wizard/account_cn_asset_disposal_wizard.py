# -*- coding: utf-8 -*-
from odoo import Command, _, fields, models
from odoo.exceptions import UserError


class AccountCnAssetDisposalWizard(models.TransientModel):
    _name = 'account.cn.asset.disposal.wizard'
    _description = '固定资产处置清理'

    asset_ids = fields.Many2many(comodel_name='account.cn.asset', string='待处置资产', required=True)
    disposal_date = fields.Date(string='处置日期', required=True, default=fields.Date.context_today)
    disposal_income = fields.Monetary(string='处置收入', currency_field='currency_id')
    disposal_expense = fields.Monetary(string='清理费用', currency_field='currency_id')
    payment_account_id = fields.Many2one(
        comodel_name='account.account', string='收付款科目',
        domain="[('account_type', '=', 'asset_cash')]",
        help='处置收入/清理费用对应的银行或现金科目，两者任一非零时必填。',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency', default=lambda self: self.env.company.currency_id,
    )

    def action_confirm(self):
        self.ensure_one()
        if (self.disposal_income or self.disposal_expense) and not self.payment_account_id:
            raise UserError(_('存在处置收入或清理费用时，必须选择收付款科目。'))

        Account = self.env['account.account']
        income_account = Account.search([
            ('company_ids', 'in', self.env.company.id), ('code', '=', '6115'),
        ], limit=1)
        if not income_account:
            raise UserError(_('未找到"资产处置收益"科目（编码 6115），请先在科目表中补充该科目。'))

        moves = self.env['account.move']
        for asset in self.asset_ids:
            if asset.state != 'running':
                raise UserError(_('只有"使用中"的资产才能处置：%s') % asset.name)
            category = asset.category_id

            # 第一步：净值/累计折旧/累计减值全部转入固定资产清理，原值转出
            step1_lines = [
                Command.create({
                    'account_id': category.disposal_account_id.id,
                    'debit': asset.net_book_value, 'credit': 0.0, 'name': _('净值转入清理'),
                }),
                Command.create({
                    'account_id': category.depreciation_account_id.id,
                    'debit': asset.accumulated_depreciation, 'credit': 0.0, 'name': _('累计折旧转出'),
                }),
            ]
            if asset.accumulated_impairment:
                step1_lines.append(Command.create({
                    'account_id': category.impairment_account_id.id,
                    'debit': asset.accumulated_impairment, 'credit': 0.0, 'name': _('减值准备转出'),
                }))
            step1_lines.append(Command.create({
                'account_id': category.fixed_asset_account_id.id,
                'debit': 0.0, 'credit': asset.original_value, 'name': _('原值转出'),
            }))
            move1 = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': category.journal_id.id,
                'company_id': asset.company_id.id,
                'date': self.disposal_date,
                'ref': _('%s：转入固定资产清理') % asset.name,
                'line_ids': step1_lines,
            })
            move1.action_post()

            # 第二步：处置收入/清理费用与清理科目轧差，结转"资产处置损益"
            # clearing_balance > 0：清理科目仍为借方余额 = 净损失；< 0：贷方余额 = 净收益
            clearing_balance = asset.net_book_value + self.disposal_expense - self.disposal_income
            step2_lines = []
            if self.disposal_income:
                step2_lines.append(Command.create({
                    'account_id': self.payment_account_id.id,
                    'debit': self.disposal_income, 'credit': 0.0, 'name': _('处置收入'),
                }))
                step2_lines.append(Command.create({
                    'account_id': category.disposal_account_id.id,
                    'debit': 0.0, 'credit': self.disposal_income, 'name': _('处置收入'),
                }))
            if self.disposal_expense:
                step2_lines.append(Command.create({
                    'account_id': category.disposal_account_id.id,
                    'debit': self.disposal_expense, 'credit': 0.0, 'name': _('清理费用'),
                }))
                step2_lines.append(Command.create({
                    'account_id': self.payment_account_id.id,
                    'debit': 0.0, 'credit': self.disposal_expense, 'name': _('清理费用'),
                }))
            if clearing_balance > 0:
                step2_lines.append(Command.create({
                    'account_id': income_account.id,
                    'debit': clearing_balance, 'credit': 0.0, 'name': _('处置净损失'),
                }))
                step2_lines.append(Command.create({
                    'account_id': category.disposal_account_id.id,
                    'debit': 0.0, 'credit': clearing_balance, 'name': _('结转处置损益'),
                }))
            elif clearing_balance < 0:
                step2_lines.append(Command.create({
                    'account_id': category.disposal_account_id.id,
                    'debit': -clearing_balance, 'credit': 0.0, 'name': _('结转处置损益'),
                }))
                step2_lines.append(Command.create({
                    'account_id': income_account.id,
                    'debit': 0.0, 'credit': -clearing_balance, 'name': _('处置净收益'),
                }))
            move2 = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': category.journal_id.id,
                'company_id': asset.company_id.id,
                'date': self.disposal_date,
                'ref': _('%s：处置损益结转') % asset.name,
                'line_ids': step2_lines,
            })
            move2.action_post()

            asset.write({'state': 'disposed'})
            moves |= move1 | move2

        return {
            'type': 'ir.actions.act_window',
            'name': _('处置凭证'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
        }
