# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .account_cn_asset_category import METHOD_SELECTION


class AccountCnAsset(models.Model):
    _name = 'account.cn.asset'
    _description = '固定资产'
    _inherit = ['mail.thread']
    _order = 'code'

    name = fields.Char(string='资产名称', required=True, tracking=True)
    code = fields.Char(string='资产编码', required=True, copy=False)
    category_id = fields.Many2one(
        comodel_name='account.cn.asset.category', string='资产类别', required=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', string='币种')
    department_id = fields.Many2one(comodel_name='hr.department', string='使用部门')
    purchase_date = fields.Date(string='购入日期', required=True, default=fields.Date.context_today)
    start_date = fields.Date(string='开始计提折旧日期', required=True, default=fields.Date.context_today)

    original_value = fields.Monetary(string='原值', required=True, currency_field='currency_id')
    salvage_rate = fields.Float(string='净残值率（%）')
    salvage_value = fields.Monetary(
        string='净残值', compute='_compute_salvage_value', store=True, readonly=False,
        currency_field='currency_id',
    )
    useful_life_years = fields.Integer(string='预计使用年限（年）', required=True, default=5)
    total_workload = fields.Float(string='预计总工作量', help='仅工作量法使用，如总里程、总工时、总产量。')
    method = fields.Selection(selection=METHOD_SELECTION, string='折旧方法', required=True)

    state = fields.Selection(
        selection=[
            ('draft', '草稿'),
            ('running', '使用中'),
            ('disposed', '已处置'),
            ('written_off', '盘亏核销'),
        ],
        string='状态', default='draft', required=True, tracking=True, copy=False,
    )

    depreciation_line_ids = fields.One2many(
        comodel_name='account.cn.asset.depreciation.line', inverse_name='asset_id',
        string='折旧计提明细',
    )
    transfer_ids = fields.One2many(
        comodel_name='account.cn.asset.transfer', inverse_name='asset_id', string='调拨记录',
    )
    impairment_ids = fields.One2many(
        comodel_name='account.cn.asset.impairment', inverse_name='asset_id', string='减值记录',
    )

    depreciated_months = fields.Integer(string='已计提月数', compute='_compute_amounts', store=True)
    accumulated_depreciation = fields.Monetary(
        string='累计折旧', compute='_compute_amounts', store=True, currency_field='currency_id',
    )
    accumulated_impairment = fields.Monetary(
        string='累计减值', compute='_compute_amounts', store=True, currency_field='currency_id',
    )
    net_book_value = fields.Monetary(
        string='账面净值', compute='_compute_amounts', store=True, currency_field='currency_id',
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', '同一公司下资产编码不能重复。'),
    ]

    @api.constrains('useful_life_years', 'method', 'total_workload')
    def _check_depreciation_inputs(self):
        for asset in self:
            if asset.useful_life_years <= 0:
                raise ValidationError(_('"%s"：预计使用年限必须大于 0，否则无法计算折旧。') % asset.name)
            if asset.method == 'workload' and asset.total_workload <= 0:
                raise ValidationError(_('"%s"：工作量法必须填写大于 0 的预计总工作量。') % asset.name)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            self.method = self.category_id.method
            self.useful_life_years = self.category_id.default_useful_life_years
            self.salvage_rate = self.category_id.default_salvage_rate

    @api.depends('original_value', 'salvage_rate')
    def _compute_salvage_value(self):
        for asset in self:
            asset.salvage_value = asset.original_value * (asset.salvage_rate or 0.0) / 100.0

    @api.depends('depreciation_line_ids.depreciation_amount', 'depreciation_line_ids.state',
                 'impairment_ids.amount', 'original_value')
    def _compute_amounts(self):
        for asset in self:
            posted_lines = asset.depreciation_line_ids.filtered(lambda l: l.state == 'posted')
            asset.accumulated_depreciation = sum(posted_lines.mapped('depreciation_amount'))
            asset.accumulated_impairment = sum(asset.impairment_ids.mapped('amount'))
            asset.depreciated_months = len(posted_lines)
            asset.net_book_value = (
                asset.original_value - asset.accumulated_depreciation - asset.accumulated_impairment
            )

    def action_confirm(self):
        for asset in self:
            if asset.state != 'draft':
                continue
            asset.state = 'running'

    def action_reset_to_draft(self):
        for asset in self:
            if asset.depreciation_line_ids.filtered(lambda l: l.state == 'posted'):
                continue
            asset.state = 'draft'

    def _cn_compute_next_depreciation_amount(self, workload_amount=0.0):
        """按当前账面状态（含已发生的减值）计算下一期折旧金额，不生成记录。
        每次都基于"当前状态"现算，而不是提前生成整张排期表，这样减值发生
        后下一期自然会用新的净值/剩余年限重算，不需要另外处理"作废重排"。"""
        self.ensure_one()
        depreciable_base = self.original_value - self.salvage_value - self.accumulated_impairment
        remaining_value = self.net_book_value - self.salvage_value
        total_months = self.useful_life_years * 12
        remaining_months = total_months - self.depreciated_months

        if remaining_months <= 0 or remaining_value <= 0:
            return 0.0

        if self.method == 'straight_line':
            amount = remaining_value / remaining_months
        elif self.method == 'workload':
            if not self.total_workload:
                amount = 0.0
            else:
                unit_amount = (self.original_value - self.salvage_value) / self.total_workload
                amount = unit_amount * workload_amount
        elif self.method == 'ddb':
            if remaining_months <= 24:
                # 企业会计准则要求：折旧年限到期前两年内改为平均摊销剩余净值
                amount = remaining_value / remaining_months
            else:
                annual_rate = 2.0 / self.useful_life_years if self.useful_life_years else 0.0
                amount = self.net_book_value * annual_rate / 12.0
        elif self.method == 'syd':
            year_index = self.depreciated_months // 12
            n = self.useful_life_years
            sum_of_years = n * (n + 1) / 2.0 if n else 1.0
            current_year_rate = (n - year_index) / sum_of_years if sum_of_years else 0.0
            amount = depreciable_base * current_year_rate / 12.0
        else:
            amount = 0.0

        # 最后一期（或计算结果超过剩余可折旧净值时）直接用剩余净值反算，避免尾差
        if remaining_months == 1 or amount >= remaining_value:
            amount = remaining_value
        return max(amount, 0.0)
