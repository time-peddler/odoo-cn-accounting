# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        self._cn_check_budget()
        return super().button_confirm()

    def _cn_find_budget_lines(self, order, account, analytic_account_ids):
        domain = [
            ('state', '=', 'approved'),
            ('company_id', '=', order.company_id.id),
            ('budget_type', '=', 'expense'),
            ('date_from', '<=', order.date_order.date() if order.date_order else fields.Date.context_today(self)),
            ('date_to', '>=', order.date_order.date() if order.date_order else fields.Date.context_today(self)),
        ]
        budget_lines = self.env['account.cn.budget.line'].search(domain)
        return budget_lines.filtered(
            lambda bl: bl.cn_match_account(account)
            and (not bl.analytic_account_id or bl.analytic_account_id.id in analytic_account_ids)
        )

    def _cn_check_budget(self):
        company = self.env.company
        if not company.cn_budget_hard_block:
            return
        if self.env.user.has_group('account_cn_budget.group_cn_budget_override'):
            return

        errors = []
        # 同一批确认的多张订单可能都占用同一条预算行，逐条独立判断会让批量
        # 确认绕过限额，这里在本次调用范围内累加各预算行已"预占"的金额。
        pending_by_budget_line = {}
        for order in self.filtered(lambda o: o.state in ('draft', 'sent')):
            for line in order.order_line:
                if not line.product_id or not line.product_qty:
                    continue
                account = line.product_id._get_product_accounts().get('expense')
                if not account:
                    continue
                analytic_account_ids = line.distribution_analytic_account_ids.ids
                budget_lines = self._cn_find_budget_lines(order, account, analytic_account_ids)
                for budget_line in budget_lines:
                    pending = pending_by_budget_line.get(budget_line.id, 0.0)
                    if budget_line.available_amount - pending - line.price_subtotal < 0:
                        errors.append(_(
                            '采购订单 %(order)s 第 %(line)s 行：科目 %(account)s 已超出预算'
                            ' "%(budget)s" 的剩余可用金额（%(available).2f），无法确认。'
                        ) % {
                            'order': order.name,
                            'line': line.product_id.display_name,
                            'account': account.display_name,
                            'budget': budget_line.budget_id.name,
                            'available': budget_line.available_amount - pending,
                        })
                    else:
                        pending_by_budget_line[budget_line.id] = pending + line.price_subtotal

        if errors:
            raise UserError('\n'.join(errors))
