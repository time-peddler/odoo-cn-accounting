# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountCnAssetTransfer(models.Model):
    _name = 'account.cn.asset.transfer'
    _description = '固定资产调拨记录'
    _order = 'date desc, id desc'

    asset_id = fields.Many2one(
        comodel_name='account.cn.asset', string='资产', required=True, ondelete='cascade',
    )
    date = fields.Date(string='调拨日期', required=True, default=fields.Date.context_today)
    old_department_id = fields.Many2one(comodel_name='hr.department', string='原使用部门', readonly=True)
    new_department_id = fields.Many2one(comodel_name='hr.department', string='新使用部门', required=True)
    reason = fields.Char(string='调拨原因')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('asset_id') and 'old_department_id' not in vals:
                asset = self.env['account.cn.asset'].browse(vals['asset_id'])
                vals['old_department_id'] = asset.department_id.id
        transfers = super().create(vals_list)
        for transfer in transfers:
            transfer.asset_id.department_id = transfer.new_department_id.id
        return transfers
