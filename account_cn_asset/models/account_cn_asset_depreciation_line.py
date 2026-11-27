# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountCnAssetDepreciationLine(models.Model):
    _name = 'account.cn.asset.depreciation.line'
    _description = '固定资产折旧计提明细'
    _order = 'period_date, id'

    asset_id = fields.Many2one(
        comodel_name='account.cn.asset', string='资产', required=True, ondelete='cascade',
    )
    currency_id = fields.Many2one(related='asset_id.currency_id', string='币种')
    period_date = fields.Date(string='计提日期', required=True)
    workload_amount = fields.Float(string='本期工作量', help='仅工作量法资产使用。')
    depreciation_amount = fields.Monetary(string='折旧金额', currency_field='currency_id')
    move_id = fields.Many2one(comodel_name='account.move', string='折旧凭证', readonly=True, copy=False)
    state = fields.Selection(
        selection=[('draft', '草稿'), ('posted', '已过账')],
        string='状态', default='draft', required=True, copy=False,
    )
