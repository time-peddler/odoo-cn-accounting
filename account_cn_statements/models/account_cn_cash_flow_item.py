# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountCnCashFlowItem(models.Model):
    _name = 'account.cn.cash.flow.item'
    _description = '现金流量项目'
    _order = 'sequence, id'

    name = fields.Char(string='名称', required=True, translate=True)
    code = fields.Char(string='编码', required=True)
    category = fields.Selection(
        selection=[
            ('operating', '经营活动'),
            ('investing', '投资活动'),
            ('financing', '筹资活动'),
            ('fx', '汇率变动影响'),
        ],
        string='活动类别',
        required=True,
    )
    flow_direction = fields.Selection(
        selection=[
            ('inflow', '流入'),
            ('outflow', '流出'),
        ],
        string='流向',
        required=True,
    )
    sequence = fields.Integer(string='序号', default=10)
    active = fields.Boolean(string='启用', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', '现金流量项目编码不能重复。'),
    ]

    def _compute_display_name(self):
        for item in self:
            item.display_name = f'{item.code} {item.name}'
