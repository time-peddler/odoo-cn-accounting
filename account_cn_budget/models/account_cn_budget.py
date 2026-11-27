# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountCnBudget(models.Model):
    _name = 'account.cn.budget'
    _description = '预算'
    _inherit = ['mail.thread']
    _order = 'date_from desc, id desc'

    name = fields.Char(string='预算名称', required=True, tracking=True)
    date_from = fields.Date(string='开始日期', required=True, tracking=True)
    date_to = fields.Date(string='结束日期', required=True, tracking=True)
    user_id = fields.Many2one(
        comodel_name='res.users', string='编制人',
        default=lambda self: self.env.user, required=True, tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司',
        default=lambda self: self.env.company, required=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', '编制中'),
            ('submitted', '待审批'),
            ('approved', '已审批'),
        ],
        string='状态', default='draft', required=True, copy=False, tracking=True,
    )
    budget_line_ids = fields.One2many(
        comodel_name='account.cn.budget.line', inverse_name='budget_id', string='预算明细',
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for budget in self:
            if budget.date_from and budget.date_to and budget.date_from > budget.date_to:
                raise ValidationError(_('"%s"：开始日期不能晚于结束日期。') % budget.name)

    def action_submit(self):
        for budget in self:
            if budget.state != 'draft':
                continue
            if not budget.budget_line_ids:
                raise UserError(_('"%s"：请至少添加一条预算明细后再提交审批。') % budget.name)
            budget.state = 'submitted'

    def action_approve(self):
        if not self.env.user.has_group('account_cn_budget.group_cn_budget_approver'):
            raise UserError(_('你没有预算审批权限。'))

        to_approve = self.filtered(lambda b: b.state == 'submitted')
        if not to_approve:
            return

        self_made = to_approve.filtered(
            lambda b: b.user_id.id == self.env.uid and not b.company_id.cn_budget_allow_self_approve
        )
        if self_made:
            raise UserError(_(
                '编制人不能审批本人编制的预算：%s'
            ) % '、'.join(self_made.mapped('name')))

        to_approve.write({'state': 'approved'})

    def action_reject(self):
        if not self.env.user.has_group('account_cn_budget.group_cn_budget_approver'):
            raise UserError(_('你没有预算审批权限。'))
        self.filtered(lambda b: b.state == 'submitted').write({'state': 'draft'})

    def action_reset_to_draft(self):
        self.filtered(lambda b: b.state == 'approved').write({'state': 'draft'})


class AccountCnBudgetLine(models.Model):
    _name = 'account.cn.budget.line'
    _description = '预算明细'

    budget_id = fields.Many2one(
        comodel_name='account.cn.budget', string='预算', required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(related='budget_id.company_id', store=True, string='公司')
    currency_id = fields.Many2one(related='company_id.currency_id', string='币种')
    date_from = fields.Date(related='budget_id.date_from', store=True, string='开始日期')
    date_to = fields.Date(related='budget_id.date_to', store=True, string='结束日期')
    state = fields.Selection(related='budget_id.state', store=True, string='预算状态')
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account', string='辅助核算维度',
        help='部门/项目/员工等分析账户，留空代表公司级、不区分维度的预算。',
    )
    account_code_prefixes = fields.Char(
        string='科目编码', required=True,
        help='逗号分隔的科目编码前缀或区间，例如 "6602" 或 "6601.01-6601.06"。',
    )
    budget_type = fields.Selection(
        selection=[('expense', '支出'), ('revenue', '收入')],
        string='预算类型', required=True, default='expense',
    )
    planned_amount = fields.Monetary(string='预算金额', required=True, currency_field='currency_id')
    actual_amount = fields.Monetary(
        string='已发生', compute='_compute_amounts', currency_field='currency_id',
    )
    committed_amount = fields.Monetary(
        string='已占用', compute='_compute_amounts', currency_field='currency_id',
        help='已确认未开票的采购订单 + 已批准未过账的费用报销，按科目/维度近似匹配。'
             '仅支出类预算计算此项。',
    )
    available_amount = fields.Monetary(
        string='剩余可用', compute='_compute_amounts', currency_field='currency_id',
    )
    usage_rate = fields.Float(
        string='执行率', compute='_compute_amounts',
        help='(已发生+已占用) / 预算金额，以小数存储，配合 widget="percentage" 按百分比展示。',
    )

    @staticmethod
    def _parse_code_prefixes(prefixes):
        """将 "1001,1401-1406" 这样的配置展开为一组具体的科目编码前缀。"""
        tokens = []
        for part in (prefixes or '').split(','):
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                start, end = part.split('-', 1)
                start, end = start.strip(), end.strip()
                width = len(start)
                for n in range(int(start), int(end) + 1):
                    tokens.append(str(n).zfill(width))
            else:
                tokens.append(part)
        return tokens

    def _cn_code_tokens(self):
        self.ensure_one()
        return self._parse_code_prefixes(self.account_code_prefixes)

    def cn_match_account(self, account):
        """判断某个总账科目是否落在本预算行的科目编码范围内，
        供采购订单/费用报销的硬拦截逻辑反向匹配使用。"""
        self.ensure_one()
        code = account.code or ''
        return any(code.startswith(token) for token in self._cn_code_tokens())

    def _cn_analytic_line_domain(self):
        """构造用于取数的 account.analytic.line 过滤域，写法与
        account_cn_statements 里 "N-1 个 '|' + N 个条件" 展开前缀写法一致。"""
        self.ensure_one()
        tokens = self._cn_code_tokens()
        if not tokens or not self.company_id:
            return False
        domain = [('company_id', '=', self.company_id.id)]
        prefix_domain = []
        for _i in range(len(tokens) - 1):
            prefix_domain.append('|')
        for token in tokens:
            prefix_domain.append(('general_account_id.code', '=like', f'{token}%'))
        domain += prefix_domain
        domain.append(('date', '>=', self.date_from))
        domain.append(('date', '<=', self.date_to))
        if self.analytic_account_id:
            domain.append(('auto_account_id', '=', self.analytic_account_id.id))
        return domain

    def _cn_compute_committed_amount(self):
        self.ensure_one()
        if self.budget_type != 'expense' or not self._cn_code_tokens():
            return 0.0

        total = 0.0

        po_domain = [
            ('order_id.state', 'in', ('purchase', 'done')),
            ('order_id.company_id', '=', self.company_id.id),
            # date_order 是 Datetime，date_from/date_to 是 Date，
            # 用"次日零点之前"而不是直接比较日期，避免漏掉结束日当天的记录
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<', self.date_to + timedelta(days=1)),
            ('qty_to_invoice', '!=', 0),
        ]
        if self.analytic_account_id:
            po_domain.append(('distribution_analytic_account_ids', 'in', self.analytic_account_id.id))
        for po_line in self.env['purchase.order.line'].search(po_domain):
            if not po_line.product_id:
                continue
            account = po_line.product_id._get_product_accounts().get('expense')
            if not account or not self.cn_match_account(account):
                continue
            if po_line.product_qty:
                total += po_line.price_subtotal * (po_line.qty_to_invoice / po_line.product_qty)
            else:
                total += po_line.price_subtotal

        expense_domain = [
            ('state', '=', 'approved'),
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.analytic_account_id:
            expense_domain.append(('distribution_analytic_account_ids', 'in', self.analytic_account_id.id))
        for expense in self.env['hr.expense'].search(expense_domain):
            if expense.account_id and self.cn_match_account(expense.account_id):
                total += expense.total_amount

        return total

    def _compute_amounts(self):
        for line in self:
            domain = line._cn_analytic_line_domain()
            actual = 0.0
            if domain:
                rows = self.env['account.analytic.line']._read_group(domain, aggregates=['amount:sum'])
                raw = rows[0][0] if rows else 0.0
                actual = -raw if line.budget_type == 'expense' else (raw or 0.0)
            line.actual_amount = actual
            line.committed_amount = line._cn_compute_committed_amount()
            line.available_amount = line.planned_amount - line.actual_amount - line.committed_amount
            line.usage_rate = (
                (line.actual_amount + line.committed_amount) / line.planned_amount
                if line.planned_amount else 0.0
            )
