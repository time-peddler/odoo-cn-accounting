# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cn_bank_import_suspense_account_id = fields.Many2one(
        comodel_name='account.account', string='银行导入暂存科目',
        help='导入的银行流水在核销到具体应收应付款之前，对方科目暂时挂在这里，'
             '建议使用一个专门开设的"其他应收/应付款-银行导入待核销"过渡科目。',
    )
