# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cn_voucher_review_enabled = fields.Boolean(
        string='启用凭证审核', default=True,
        help='关闭后，本公司所有记账凭证均无需审核即可直接过账。',
    )
    cn_voucher_review_allow_self = fields.Boolean(
        string='允许审核本人制单的凭证',
        help='仅适用于只有一名会计人员、无法做到制单/审核分离的场景。'
             '默认关闭，符合制单人不能审核本人凭证的内控要求。',
    )
