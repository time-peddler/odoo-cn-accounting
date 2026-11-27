# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cn_credit_limit_hard_block = fields.Boolean(
        string='信用超限强制拦截',
        help='关闭时（默认）沿用 Odoo 原生行为：超出信用额度只在单据上提示，'
             '不影响确认/过账。开启后，普通用户无法确认超额客户的销售订单，'
             '也无法过账其发票，只有"信用超限审批人"用户组的成员可以继续操作。',
    )
