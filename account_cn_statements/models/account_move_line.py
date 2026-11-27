# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cn_cash_flow_item_id = fields.Many2one(
        comodel_name='account.cn.cash.flow.item',
        string='现金流量项目',
        help='仅对货币资金类科目（库存现金/银行存款/其他货币资金）的分录行有效，'
             '用于按经营/投资/筹资活动自动归集直接法现金流量表。',
    )
