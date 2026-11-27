# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountCnDisallowedExpenseCategory(models.Model):
    _name = 'account.cn.disallowed.expense.category'
    _description = '纳税调整类别'
    _order = 'code'

    name = fields.Char(string='类别名称', required=True, translate=True)
    code = fields.Char(string='类别编码', required=True)
    limit_type = fields.Selection(
        selection=[
            ('full', '全额不可扣除'),
            ('rate', '按比例扣除，超出部分调增'),
            ('rate_and_revenue_cap', '按比例且不超过营业收入一定比例，两者取低'),
        ],
        string='限额类型', required=True, default='rate',
    )
    deductible_rate = fields.Float(
        string='可扣除比例（%）',
        help='"按比例扣除"或"按比例且不超过营业收入一定比例"类型使用，'
             '例如业务招待费的 60%。',
    )
    revenue_cap_rate = fields.Float(
        string='占营业收入比例上限（%）',
        help='仅"按比例且不超过营业收入一定比例"类型使用，例如业务招待费的 0.5%。',
    )
    account_ids = fields.One2many(
        comodel_name='account.account', inverse_name='cn_disallowed_category_id', string='适用科目',
    )
    note = fields.Char(string='备注')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', '类别编码不能重复。'),
    ]

    @api.constrains('limit_type', 'deductible_rate', 'revenue_cap_rate')
    def _check_rates(self):
        for category in self:
            if category.limit_type in ('rate', 'rate_and_revenue_cap') and category.deductible_rate <= 0:
                raise ValidationError(_('"%s"：该限额类型必须填写大于 0 的可扣除比例。') % category.name)
            if category.limit_type == 'rate_and_revenue_cap' and category.revenue_cap_rate <= 0:
                raise ValidationError(_('"%s"：该限额类型必须填写大于 0 的营业收入比例上限。') % category.name)
