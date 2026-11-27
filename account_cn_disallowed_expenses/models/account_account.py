# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    cn_disallowed_category_id = fields.Many2one(
        comodel_name='account.cn.disallowed.expense.category', string='纳税调整类别',
        help='设置后，本科目的发生额会计入企业所得税汇算清缴纳税调整报表对应类别。',
    )
