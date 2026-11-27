# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_DISPOSITION_ACCOUNT_CODE = {
    'non_operating_income': '6301',   # 营业外收入
    'non_operating_expense': '6711',  # 营业外支出
    'receivable': '1221',             # 其他应收款
}


class AccountCnAssetInventoryCount(models.Model):
    _name = 'account.cn.asset.inventory.count'
    _description = '固定资产盘点盈亏'
    _order = 'count_date desc, id desc'

    count_type = fields.Selection(
        selection=[('surplus', '盘盈'), ('deficit', '盘亏')],
        string='盘点类型', required=True, default='deficit',
    )
    asset_id = fields.Many2one(
        comodel_name='account.cn.asset', string='对应资产',
        help='盘亏时必填（关联现有资产）；盘盈时留空（账外新发现的资产）。',
    )
    category_id = fields.Many2one(comodel_name='account.cn.asset.category', string='资产类别', required=True)
    name = fields.Char(string='资产名称/说明', required=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', string='币种')
    estimated_value = fields.Monetary(
        string='估值/账面净值', required=True, currency_field='currency_id',
        help='盘盈资产按重置成本或市场公允价值估值；盘亏资产自动取账面净值。',
    )
    count_date = fields.Date(string='盘点日期', required=True, default=fields.Date.context_today)
    disposition_type = fields.Selection(
        selection=[
            ('non_operating_income', '转营业外收入'),
            ('non_operating_expense', '转营业外支出'),
            ('receivable', '责任人赔偿（挂其他应收款）'),
        ],
        string='最终处理方式',
    )
    move_id = fields.Many2one(comodel_name='account.move', string='挂账凭证', readonly=True, copy=False)
    disposition_move_id = fields.Many2one(
        comodel_name='account.move', string='转销凭证', readonly=True, copy=False,
    )
    state = fields.Selection(
        selection=[
            ('draft', '草稿'),
            ('pending', '待处理（已挂账）'),
            ('done', '已转销'),
        ],
        string='状态', default='draft', required=True, copy=False,
    )

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        if self.asset_id:
            self.category_id = self.asset_id.category_id
            self.estimated_value = self.asset_id.net_book_value
            self.name = self.asset_id.name

    def _cn_find_account(self, code):
        self.ensure_one()
        Account = self.env['account.account']
        account = Account.search([
            ('company_ids', 'in', self.company_id.id), ('code', '=', code),
        ], limit=1)
        if not account:
            raise UserError(_('未找到科目编码 %s，请先在科目表中补充。') % code)
        return account

    def action_post_pending(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            pending_account = rec._cn_find_account('1901')
            if rec.count_type == 'surplus':
                lines = [
                    Command.create({
                        'account_id': rec.category_id.fixed_asset_account_id.id,
                        'debit': rec.estimated_value, 'credit': 0.0, 'name': _('盘盈入账'),
                    }),
                    Command.create({
                        'account_id': pending_account.id,
                        'debit': 0.0, 'credit': rec.estimated_value, 'name': _('待处理财产损溢'),
                    }),
                ]
            else:
                if not rec.asset_id:
                    raise UserError(_('盘亏必须关联对应的资产：%s') % rec.name)
                lines = [
                    Command.create({
                        'account_id': pending_account.id,
                        'debit': rec.estimated_value, 'credit': 0.0, 'name': _('待处理财产损溢'),
                    }),
                    Command.create({
                        'account_id': rec.category_id.disposal_account_id.id,
                        'debit': 0.0, 'credit': rec.estimated_value, 'name': _('盘亏转出净值'),
                    }),
                ]
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': rec.category_id.journal_id.id,
                'company_id': rec.company_id.id,
                'date': rec.count_date,
                'ref': _('%s：盘点挂账') % rec.name,
                'line_ids': lines,
            })
            move.action_post()
            rec.write({'move_id': move.id, 'state': 'pending'})
            if rec.count_type == 'deficit' and rec.asset_id:
                rec.asset_id.state = 'written_off'

    def action_post_disposition(self):
        for rec in self:
            if rec.state != 'pending' or not rec.disposition_type:
                continue
            pending_account = rec._cn_find_account('1901')
            target_account = rec._cn_find_account(_DISPOSITION_ACCOUNT_CODE[rec.disposition_type])
            if rec.count_type == 'surplus':
                lines = [
                    Command.create({
                        'account_id': pending_account.id,
                        'debit': rec.estimated_value, 'credit': 0.0, 'name': _('转销'),
                    }),
                    Command.create({
                        'account_id': target_account.id,
                        'debit': 0.0, 'credit': rec.estimated_value, 'name': _('盘盈转销'),
                    }),
                ]
            else:
                lines = [
                    Command.create({
                        'account_id': target_account.id,
                        'debit': rec.estimated_value, 'credit': 0.0, 'name': _('盘亏转销'),
                    }),
                    Command.create({
                        'account_id': pending_account.id,
                        'debit': 0.0, 'credit': rec.estimated_value, 'name': _('转销'),
                    }),
                ]
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': rec.category_id.journal_id.id,
                'company_id': rec.company_id.id,
                'date': fields.Date.context_today(rec),
                'ref': _('%s：盘点转销') % rec.name,
                'line_ids': lines,
            })
            move.action_post()
            rec.write({'disposition_move_id': move.id, 'state': 'done'})
