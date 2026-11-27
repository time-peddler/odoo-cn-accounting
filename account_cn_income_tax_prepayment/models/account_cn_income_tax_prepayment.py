# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# 与 account_cn_period_close 已验证过的科目类型清单保持一致
_PL_INTERNAL_GROUPS = ('income', 'expense')


class AccountCnIncomeTaxPrepayment(models.Model):
    _name = 'account.cn.income.tax.prepayment'
    _description = '企业所得税季度预缴测算'
    _order = 'date_to desc'

    name = fields.Char(string='名称', compute='_compute_name', store=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', string='币种')
    date_from = fields.Date(
        string='会计年度起始日', required=True,
        help='应为所属会计年度的年初日期，本记录的各项金额均为年初至今的累计数。',
    )
    date_to = fields.Date(string='本季度截止日', required=True)
    state = fields.Selection(
        selection=[('draft', '编制中'), ('confirmed', '已确认')],
        string='状态', default='draft', required=True, readonly=True, copy=False,
    )

    cumulative_profit = fields.Monetary(string='利润总额（累计）', currency_field='currency_id')
    tax_adjustment_amount = fields.Monetary(string='纳税调整增加额（累计）', currency_field='currency_id')
    prior_year_loss_offset = fields.Monetary(
        string='弥补以前年度亏损', currency_field='currency_id',
        help='请按税务口径自行填报，本模块不做亏损结转台账。',
    )
    prior_prepaid_cumulative = fields.Monetary(string='以前季度已预缴（累计）', currency_field='currency_id')

    taxable_income = fields.Monetary(
        string='应纳税所得额', compute='_compute_tax_amounts', store=True, currency_field='currency_id',
    )
    tax_payable_cumulative = fields.Monetary(
        string='本年累计应预缴所得税额', compute='_compute_tax_amounts', store=True, currency_field='currency_id',
    )
    current_quarter_tax_due = fields.Monetary(
        string='本季度应补(退)预缴税额', compute='_compute_tax_amounts', store=True, currency_field='currency_id',
    )

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for record in self:
            if record.date_to:
                record.name = _('截至 %s 企业所得税预缴测算') % record.date_to
            else:
                record.name = _('企业所得税预缴测算')

    @api.constrains('date_from', 'date_to', 'company_id')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(_('"%s"：会计年度起始日不能晚于本季度截止日。') % record.name)
            overlapping = self.search_count([
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id),
                ('date_from', '=', record.date_from),
                ('date_to', '=', record.date_to),
            ])
            if overlapping:
                raise ValidationError(_('该公司在此期间内已存在同样的预缴测算记录，请勿重复编制。'))

    @api.depends('cumulative_profit', 'tax_adjustment_amount', 'prior_year_loss_offset',
                 'prior_prepaid_cumulative', 'company_id.cn_income_tax_rate')
    def _compute_tax_amounts(self):
        for record in self:
            taxable_income = (
                record.cumulative_profit + record.tax_adjustment_amount - record.prior_year_loss_offset
            )
            record.taxable_income = taxable_income
            tax_payable = max(0.0, taxable_income) * (record.company_id.cn_income_tax_rate or 0.0) / 100.0
            record.tax_payable_cumulative = tax_payable
            record.current_quarter_tax_due = tax_payable - record.prior_prepaid_cumulative

    def _cn_compute_cumulative_profit(self):
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('account_id.internal_group', 'in', _PL_INTERNAL_GROUPS),
        ]
        rows = self.env['account.move.line']._read_group(domain, aggregates=['debit:sum', 'credit:sum'])
        debit_sum, credit_sum = rows[0] if rows else (0.0, 0.0)
        # 借-贷：损益类科目净额为负数代表净利润，取反得到利润总额
        return -(debit_sum - credit_sum)

    def _cn_compute_tax_adjustment(self):
        self.ensure_one()
        if 'account.cn.disallowed.expense.report' in self.env:
            return self.env['account.cn.disallowed.expense.report'].get_cumulative_adjustment(
                self.company_id.id, self.date_from, self.date_to,
            )
        return self.tax_adjustment_amount

    def _cn_find_prior_prepayment(self):
        self.ensure_one()
        return self.search([
            ('id', '!=', self.id),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'confirmed'),
            ('date_from', '=', self.date_from),
            ('date_to', '<', self.date_to),
        ], order='date_to desc', limit=1)

    def action_generate(self):
        for record in self.filtered(lambda r: r.state == 'draft'):
            prior = record._cn_find_prior_prepayment()
            record.write({
                'cumulative_profit': record._cn_compute_cumulative_profit(),
                'tax_adjustment_amount': record._cn_compute_tax_adjustment(),
                'prior_prepaid_cumulative': prior.tax_payable_cumulative if prior else 0.0,
            })

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('只有编制中的测算记录才能确认。'))
            record.state = 'confirmed'

    def action_reset_to_draft(self):
        self.filtered(lambda r: r.state == 'confirmed').write({'state': 'draft'})
