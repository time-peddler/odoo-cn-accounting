# -*- coding: utf-8 -*-
from odoo import models


class AccountCnStatementLine(models.Model):
    _inherit = 'account.cn.statement.line'

    def _build_amount_domain(self, company, date_from, date_to):
        domain = super()._build_amount_domain(company, date_from, date_to)
        # 结转凭证已经把当期损益类科目发生额清零并转入本年利润，若不排除会导致
        # 利润表"本期发生额"被结转凭证自身重复冲抵。资产负债表按累计余额取数，
        # 结转凭证对本年利润余额的影响应当保留，因此只对利润表做排除。
        if domain and self.statement_id.code == 'income_statement':
            domain = domain + [('journal_id.is_period_closing', '=', False)]
        return domain
