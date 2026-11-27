# -*- coding: utf-8 -*-
from odoo import api, fields, models

# (公司字段名, l10n_cn 科目编码)，用于安装/升级时自动查找并回填默认值
_ACCOUNT_CODE_MAP = [
    ('cn_notes_receivable_account_id', '1121'),
    ('cn_notes_payable_account_id', '2201'),
    ('cn_bill_interest_expense_account_id', '5603.01'),
    ('cn_bill_financing_account_id', '2001'),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    cn_notes_receivable_account_id = fields.Many2one(
        comodel_name='account.account', string='应收票据科目',
    )
    cn_notes_payable_account_id = fields.Many2one(
        comodel_name='account.account', string='应付票据科目',
    )
    cn_bill_interest_expense_account_id = fields.Many2one(
        comodel_name='account.account', string='票据贴现利息费用科目',
        help='贴现时确认的利息费用（财务费用-利息费用）。',
    )
    cn_bill_financing_account_id = fields.Many2one(
        comodel_name='account.account', string='票据贴现融资科目',
        help='商业承兑汇票按"融资法"贴现时，贴现所得计入的短期借款科目。',
    )

    @api.model
    def _cn_set_default_bill_accounts(self):
        """按 l10n_cn 科目表自动回填票据相关科目，仅在未配置时才设置，
        不覆盖用户已手工调整过的配置；找不到对应科目的公司直接跳过，不报错。"""
        Account = self.env['account.account']
        for company in self.env['res.company'].search([]):
            vals = {}
            for field_name, code in _ACCOUNT_CODE_MAP:
                if company[field_name]:
                    continue
                account = Account.search([
                    ('company_ids', 'in', company.id), ('code', '=', code),
                ], limit=1)
                if account:
                    vals[field_name] = account.id
            if vals:
                company.write(vals)
