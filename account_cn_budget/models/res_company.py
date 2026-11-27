# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cn_budget_hard_block = fields.Boolean(
        string='超预算强制拦截',
        help='关闭时（默认），预算只用于统计对比，不影响采购订单确认、费用报销审批。'
             '开启后，普通用户无法确认/审批会导致超出已审批预算余额的采购订单/费用报销，'
             '只有"预算超支审批人"用户组的成员可以继续操作。',
    )
    cn_budget_allow_self_approve = fields.Boolean(
        string='允许审批本人编制的预算',
        help='默认关闭，符合编制人不能审批本人预算的内控要求；'
             '仅适用于只有一名预算编制人员、无法做到编制/审批分离的场景。',
    )
