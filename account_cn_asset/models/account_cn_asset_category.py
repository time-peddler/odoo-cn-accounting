# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# (类别编码, 类别名称, 固定资产科目编码, 累计折旧科目编码, 折旧费用科目编码,
#  固定资产清理科目编码, 固定资产减值准备科目编码)
# 编码均取自 l10n_cn 企业会计准则科目表，六个子类别与科目一一对应。
_CATEGORY_DEFS = [
    ('BUILDING', '房屋建筑物', '1601.01', '1602.01', '6602.02.01', '1606.01', '1603.01'),
    ('MACHINERY', '机器设备', '1601.02', '1602.02', '6602.02.02', '1606.02', '1603.02'),
    ('VEHICLE', '运输设备', '1601.03', '1602.03', '6602.02.03', '1606.03', '1603.03'),
    ('ELECTRONIC', '电子设备', '1601.04', '1602.04', '6602.02.04', '1606.04', '1603.04'),
    ('OFFICE', '办公设备', '1601.05', '1602.05', '6602.02.05', '1606.05', '1603.05'),
    ('OTHER', '其他固定资产', '1601.06', '1602.06', '6602.02.06', '1606.06', '1603.06'),
]

METHOD_SELECTION = [
    ('straight_line', '年限平均法'),
    ('workload', '工作量法'),
    ('ddb', '双倍余额递减法'),
    ('syd', '年数总和法'),
]


class AccountCnAssetCategory(models.Model):
    _name = 'account.cn.asset.category'
    _description = '固定资产类别'
    _order = 'code'

    name = fields.Char(string='类别名称', required=True, translate=True)
    code = fields.Char(string='类别编码', required=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    fixed_asset_account_id = fields.Many2one(
        comodel_name='account.account', string='固定资产科目', required=True,
        domain="[('account_type', '=', 'asset_fixed')]",
    )
    depreciation_account_id = fields.Many2one(
        comodel_name='account.account', string='累计折旧科目', required=True,
        domain="[('account_type', '=', 'asset_fixed')]",
    )
    depreciation_expense_account_id = fields.Many2one(
        comodel_name='account.account', string='折旧费用科目', required=True,
        domain="[('account_type', 'in', ('expense', 'expense_depreciation', 'expense_direct_cost'))]",
    )
    disposal_account_id = fields.Many2one(
        comodel_name='account.account', string='固定资产清理科目', required=True,
        domain="[('account_type', '=', 'asset_fixed')]",
    )
    impairment_account_id = fields.Many2one(
        comodel_name='account.account', string='固定资产减值准备科目', required=True,
        domain="[('account_type', '=', 'asset_fixed')]",
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal', string='日记账', required=True,
        domain="[('type', '=', 'general')]",
    )
    method = fields.Selection(
        selection=METHOD_SELECTION, string='默认折旧方法',
        default='straight_line', required=True,
    )
    default_useful_life_years = fields.Integer(string='默认使用年限（年）', default=5)
    default_salvage_rate = fields.Float(string='默认净残值率（%）', default=5.0)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', '同一公司下类别编码不能重复。'),
    ]

    @api.constrains(
        'fixed_asset_account_id', 'depreciation_account_id',
        'disposal_account_id', 'impairment_account_id',
    )
    def _check_distinct_accounts(self):
        for category in self:
            accounts = (
                category.fixed_asset_account_id
                | category.depreciation_account_id
                | category.disposal_account_id
                | category.impairment_account_id
            )
            if len(accounts) < 4:
                raise ValidationError(_(
                    '"%s"：固定资产科目、累计折旧科目、固定资产清理科目、固定资产减值准备科目'
                    '必须是四个不同的科目，不能重复选择同一个。'
                ) % category.name)

    def _cn_get_or_create_journal(self, company):
        journal = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('code', '=', 'ZCJZ'),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].create({
                'name': '固定资产折旧',
                'code': 'ZCJZ',
                'type': 'general',
                'company_id': company.id,
            })
        return journal

    @api.model
    def _cn_create_default_categories(self):
        """按 l10n_cn 科目表自动创建/刷新六个标准资产类别，每个公司各一套。
        每次安装/升级本模块都会重新执行，缺失科目的公司会被跳过（不报错）。"""
        Account = self.env['account.account']
        for company in self.env['res.company'].search([]):
            journal = None
            for code, name, fixed_code, dep_code, exp_code, disposal_code, impair_code in _CATEGORY_DEFS:
                accounts = {}
                ok = True
                for key, acc_code in (
                    ('fixed_asset_account_id', fixed_code),
                    ('depreciation_account_id', dep_code),
                    ('depreciation_expense_account_id', exp_code),
                    ('disposal_account_id', disposal_code),
                    ('impairment_account_id', impair_code),
                ):
                    account = Account.search([
                        ('company_ids', 'in', company.id), ('code', '=', acc_code),
                    ], limit=1)
                    if not account:
                        ok = False
                        break
                    accounts[key] = account.id
                if not ok:
                    continue
                if journal is None:
                    journal = self._cn_get_or_create_journal(company)
                vals = dict(accounts, code=code, name=name, company_id=company.id, journal_id=journal.id)
                existing = self.search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    self.create(vals)
