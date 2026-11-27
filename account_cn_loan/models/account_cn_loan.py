# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

REPAYMENT_METHOD_SELECTION = [
    ('equal_principal', '等额本金'),
    ('equal_installment', '等额本息'),
    ('interest_only', '先息后本'),
]


class AccountCnLoan(models.Model):
    _name = 'account.cn.loan'
    _description = '借款'
    _inherit = ['mail.thread']
    _order = 'start_date desc'

    name = fields.Char(string='借款名称', required=True, tracking=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string='贷款方')
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', string='币种')
    loan_type = fields.Selection(
        selection=[('short_term', '短期借款'), ('long_term', '长期借款')],
        string='借款类型', required=True, default='short_term', tracking=True,
    )
    principal_amount = fields.Monetary(string='借款本金', required=True, currency_field='currency_id')
    start_date = fields.Date(string='起始日期', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='到期日期', required=True)
    annual_interest_rate = fields.Float(string='年利率（%）', required=True)
    repayment_method = fields.Selection(
        selection=REPAYMENT_METHOD_SELECTION, string='还款方式', required=True, default='equal_principal',
    )
    total_periods = fields.Integer(string='总期数（月）', required=True, default=12)
    monthly_payment = fields.Monetary(
        string='每期月供', currency_field='currency_id', readonly=True, copy=False,
        help='仅等额本息方式使用，确认借款时按标准年金公式一次性算出并存储。',
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal', string='银行日记账', required=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
        help='借款到账、还本付息均使用此日记账的默认科目。',
    )
    loan_account_id = fields.Many2one(
        comodel_name='account.account', string='借款科目', required=True,
        help='短期借款或长期借款科目，与"借款类型"对应。',
    )
    interest_expense_account_id = fields.Many2one(
        comodel_name='account.account', string='利息费用科目', required=True,
    )
    current_portion_account_id = fields.Many2one(
        comodel_name='account.account', string='一年内到期的非流动负债科目',
        help='仅长期借款使用，用于月末重分类。标准 l10n_cn 科目表没有此科目，'
             '留空则不启用重分类功能，不是缺陷。',
    )
    state = fields.Selection(
        selection=[('draft', '草稿'), ('running', '还款中'), ('closed', '已结清')],
        string='状态', default='draft', required=True, tracking=True, copy=False,
    )
    move_id = fields.Many2one(comodel_name='account.move', string='借款到账分录', readonly=True, copy=False)
    repayment_line_ids = fields.One2many(
        comodel_name='account.cn.loan.repayment.line', inverse_name='loan_id', string='还款计提明细',
    )

    repaid_periods = fields.Integer(
        string='已还期数', compute='_compute_amounts', store=True,
    )
    repaid_principal = fields.Monetary(
        string='累计已还本金', compute='_compute_amounts', store=True, currency_field='currency_id',
    )
    remaining_principal = fields.Monetary(
        string='剩余本金', compute='_compute_amounts', store=True, currency_field='currency_id',
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for loan in self:
            if loan.start_date and loan.end_date and loan.start_date > loan.end_date:
                raise ValidationError(_('"%s"：起始日期不能晚于到期日期。') % loan.name)

    @api.constrains('total_periods')
    def _check_total_periods(self):
        for loan in self:
            if loan.total_periods <= 0:
                raise ValidationError(_('"%s"：总期数必须大于 0。') % loan.name)

    @api.depends('repayment_line_ids.principal_amount', 'repayment_line_ids.state', 'principal_amount')
    def _compute_amounts(self):
        for loan in self:
            posted_lines = loan.repayment_line_ids.filtered(lambda l: l.state == 'posted')
            loan.repaid_periods = len(posted_lines)
            loan.repaid_principal = sum(posted_lines.mapped('principal_amount'))
            loan.remaining_principal = loan.principal_amount - loan.repaid_principal

    def _cn_monthly_rate(self):
        self.ensure_one()
        return (self.annual_interest_rate or 0.0) / 100.0 / 12.0

    def action_confirm(self):
        for loan in self.filtered(lambda l: l.state == 'draft'):
            if not loan.journal_id.default_account_id:
                raise UserError(_('"%s"：所选银行日记账未配置默认科目。') % loan.name)
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': loan.journal_id.id,
                'company_id': loan.company_id.id,
                'partner_id': loan.partner_id.id,
                'date': loan.start_date,
                'ref': _('借款到账：%s') % loan.name,
                'line_ids': [
                    Command.create({
                        'account_id': loan.journal_id.default_account_id.id,
                        'debit': loan.principal_amount, 'credit': 0.0, 'name': loan.name,
                    }),
                    Command.create({
                        'account_id': loan.loan_account_id.id,
                        'debit': 0.0, 'credit': loan.principal_amount, 'name': loan.name,
                    }),
                ],
            })
            move.action_post()

            monthly_payment = 0.0
            if loan.repayment_method == 'equal_installment':
                rate = loan._cn_monthly_rate()
                n = loan.total_periods
                if rate:
                    factor = (1 + rate) ** n
                    monthly_payment = loan.principal_amount * rate * factor / (factor - 1)
                else:
                    monthly_payment = loan.principal_amount / n

            loan.write({'move_id': move.id, 'state': 'running', 'monthly_payment': monthly_payment})

    def action_close(self):
        self.filtered(lambda l: l.state == 'running').write({'state': 'closed'})

    def _cn_compute_next_repayment(self):
        """按当前剩余本金/已还期数现算下一期的本金、利息拆分，不预生成整张排期表。"""
        self.ensure_one()
        remaining = self.remaining_principal
        remaining_periods = self.total_periods - self.repaid_periods
        rate = self._cn_monthly_rate()

        if remaining_periods <= 0 or self.currency_id.is_zero(remaining):
            return 0.0, 0.0

        if self.repayment_method == 'equal_principal':
            principal = self.principal_amount / self.total_periods
            interest = remaining * rate
        elif self.repayment_method == 'equal_installment':
            interest = remaining * rate
            principal = self.monthly_payment - interest
        elif self.repayment_method == 'interest_only':
            interest = remaining * rate
            principal = remaining if remaining_periods == 1 else 0.0
        else:
            principal, interest = 0.0, 0.0

        if remaining_periods == 1 or principal >= remaining:
            principal = remaining
        return principal, max(interest, 0.0)

    def _cn_forecast_principal_within_months(self, months):
        """预测未来 N 个月内到期的本金合计，供长期借款重分类/资金预测使用；
        纯预测计算，不改变任何存量状态。"""
        self.ensure_one()
        remaining = self.remaining_principal
        repaid = self.repaid_periods
        total = 0.0
        for _i in range(min(months, max(self.total_periods - repaid, 0))):
            remaining_periods = self.total_periods - repaid
            rate = self._cn_monthly_rate()
            if remaining_periods <= 0 or self.currency_id.is_zero(remaining):
                break
            if self.repayment_method == 'equal_principal':
                principal = self.principal_amount / self.total_periods
            elif self.repayment_method == 'equal_installment':
                interest = remaining * rate
                principal = self.monthly_payment - interest
            else:
                principal = remaining if remaining_periods == 1 else 0.0
            if remaining_periods == 1 or principal >= remaining:
                principal = remaining
            total += principal
            remaining -= principal
            repaid += 1
        return total

    def _cn_forecast_repayment_schedule(self, date_from, date_to):
        """按当前状态模拟未来还款计划（不改变任何存量状态），供资金预测使用。
        返回 [{'date', 'principal', 'interest'}, ...]，只包含落在
        [date_from, date_to] 区间内的期次。"""
        self.ensure_one()
        remaining = self.remaining_principal
        repaid = self.repaid_periods
        rate = self._cn_monthly_rate()
        schedule = []
        while repaid < self.total_periods and not self.currency_id.is_zero(remaining):
            period_date = self.start_date + relativedelta(months=repaid + 1)
            if period_date > date_to:
                break
            remaining_periods = self.total_periods - repaid
            interest = remaining * rate
            if self.repayment_method == 'equal_principal':
                principal = self.principal_amount / self.total_periods
            elif self.repayment_method == 'equal_installment':
                principal = self.monthly_payment - interest
            else:
                principal = remaining if remaining_periods == 1 else 0.0
            if remaining_periods == 1 or principal >= remaining:
                principal = remaining
            if period_date >= date_from:
                schedule.append({'date': period_date, 'principal': principal, 'interest': interest})
            remaining -= principal
            repaid += 1
        return schedule

    def _cn_get_reclass_journal(self, company):
        journal = self.env['account.journal'].search([
            ('company_id', '=', company.id), ('code', '=', 'LNRC'),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].create({
                'name': _('借款重分类'),
                'code': 'LNRC',
                'type': 'general',
                'company_id': company.id,
            })
        return journal

    def _cn_reclassify_current_portion(self, date):
        """长期借款一年内到期部分重分类：借长期借款/贷一年内到期的非流动负债，
        并生成次日自动红冲分录，下次执行时用新的合计数重新走一遍，不需要
        维护"上次重分类了多少"这类状态。仅 current_portion_account_id 已配置
        时才执行；按月去重，避免同月内重复运行向导产生多组配对分录。"""
        self.ensure_one()
        if not self.current_portion_account_id:
            return
        ref = _('长期借款一年内到期部分重分类：%(loan)s %(month)s') % {
            'loan': self.name, 'month': date.strftime('%Y-%m'),
        }
        existing = self.env['account.move'].search([
            ('ref', '=', ref), ('company_id', '=', self.company_id.id),
        ], limit=1)
        if existing:
            return
        amount = self._cn_forecast_principal_within_months(12)
        if self.currency_id.is_zero(amount):
            return

        journal = self._cn_get_reclass_journal(self.company_id)
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'date': date,
            'ref': ref,
            'line_ids': [
                Command.create({
                    'account_id': self.loan_account_id.id,
                    'debit': amount, 'credit': 0.0, 'name': ref,
                }),
                Command.create({
                    'account_id': self.current_portion_account_id.id,
                    'debit': 0.0, 'credit': amount, 'name': ref,
                }),
            ],
        })
        move.action_post()

        reversal = move._reverse_moves(default_values_list=[{
            'date': date + relativedelta(days=1),
            'ref': _('自动红冲：%s') % ref,
        }])
        reversal.action_post()
