# -*- coding: utf-8 -*-
from odoo import api, models


class AccountCnDisallowedExpenseReport(models.AbstractModel):
    _name = 'account.cn.disallowed.expense.report'
    _description = '纳税调整/不可抵扣费用报表'

    @api.model
    def _cn_revenue_amount(self, company_id, date_from, date_to):
        domain = [
            ('company_id', '=', company_id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('account_id.account_type', '=', 'income'),
        ]
        rows = self.env['account.move.line']._read_group(domain, aggregates=['debit:sum', 'credit:sum'])
        debit_sum, credit_sum = rows[0] if rows else (0.0, 0.0)
        return credit_sum - debit_sum

    @api.model
    def get_report_data(self, company_id, date_from, date_to):
        """company_id 为空（前端报表调用场景）时取当前会话的活动公司；
        跨模块调用（如 account_cn_income_tax_prepayment）应始终显式传入目标
        记录所属的公司，不依赖会话上下文。"""
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company
        company_id = company.id
        categories = self.env['account.cn.disallowed.expense.category'].search([
            ('account_ids', '!=', False),
        ])
        revenue_amount = None
        rows = []
        totals = {'actual_amount': 0.0, 'deductible_amount': 0.0, 'adjustment_amount': 0.0}

        for category in categories:
            accounts = category.account_ids
            base_domain = [
                ('company_id', '=', company_id),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('account_id', 'in', accounts.ids),
            ]
            agg_rows = self.env['account.move.line']._read_group(base_domain, aggregates=['debit:sum', 'credit:sum'])
            debit_sum, credit_sum = agg_rows[0] if agg_rows else (0.0, 0.0)
            actual_amount = debit_sum - credit_sum
            if company.currency_id.is_zero(actual_amount):
                continue

            if category.limit_type == 'full':
                deductible_amount = 0.0
            elif category.limit_type == 'rate':
                deductible_amount = actual_amount * category.deductible_rate / 100.0
            else:
                if revenue_amount is None:
                    revenue_amount = self._cn_revenue_amount(company_id, date_from, date_to)
                deductible_amount = min(
                    actual_amount * category.deductible_rate / 100.0,
                    revenue_amount * category.revenue_cap_rate / 100.0,
                )
            adjustment_amount = actual_amount - deductible_amount

            row = {
                'category_id': category.id,
                'category_name': category.name,
                'actual_amount': actual_amount,
                'deductible_amount': deductible_amount,
                'adjustment_amount': adjustment_amount,
                'drilldown_domain': base_domain,
            }
            rows.append(row)
            totals['actual_amount'] += actual_amount
            totals['deductible_amount'] += deductible_amount
            totals['adjustment_amount'] += adjustment_amount

        return {'rows': rows, 'totals': totals}

    @api.model
    def get_cumulative_adjustment(self, company_id, date_from, date_to):
        data = self.get_report_data(company_id, date_from, date_to)
        return data['totals']['adjustment_amount']
