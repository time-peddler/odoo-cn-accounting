# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def action_approve(self):
        self._cn_check_budget()
        return super().action_approve()

    def _cn_find_budget_lines(self, expense, analytic_account_ids):
        expense_date = expense.date or fields.Date.context_today(self)
        domain = [
            ('state', '=', 'approved'),
            ('company_id', '=', expense.company_id.id),
            ('budget_type', '=', 'expense'),
            ('date_from', '<=', expense_date),
            ('date_to', '>=', expense_date),
        ]
        budget_lines = self.env['account.cn.budget.line'].search(domain)
        return budget_lines.filtered(
            lambda bl: bl.cn_match_account(expense.account_id)
            and (not bl.analytic_account_id or bl.analytic_account_id.id in analytic_account_ids)
        )

    def _cn_check_budget(self):
        company = self.env.company
        if not company.cn_budget_hard_block:
            return
        if self.env.user.has_group('account_cn_budget.group_cn_budget_override'):
            return

        errors = []
        # 同一批审批的多张报销单可能都占用同一条预算行，逐条独立判断会让批量
        # 审批绕过限额，这里在本次调用范围内累加各预算行已"预占"的金额。
        pending_by_budget_line = {}
        for expense in self.filtered(lambda e: e.account_id):
            analytic_account_ids = expense.distribution_analytic_account_ids.ids
            budget_lines = self._cn_find_budget_lines(expense, analytic_account_ids)
            for budget_line in budget_lines:
                pending = pending_by_budget_line.get(budget_line.id, 0.0)
                if budget_line.available_amount - pending - expense.total_amount < 0:
                    errors.append(_(
                        '费用报销 "%(expense)s"：科目 %(account)s 已超出预算'
                        ' "%(budget)s" 的剩余可用金额（%(available).2f），无法审批。'
                    ) % {
                        'expense': expense.name,
                        'account': expense.account_id.display_name,
                        'budget': budget_line.budget_id.name,
                        'available': budget_line.available_amount - pending,
                    })
                else:
                    pending_by_budget_line[budget_line.id] = pending + expense.total_amount

        if errors:
            raise UserError('\n'.join(errors))
