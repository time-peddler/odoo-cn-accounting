# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# 结转凭证只处理损益类科目（收入/费用），不涉及资产、负债、共同类、所有者权益
_PL_INTERNAL_GROUPS = ('income', 'expense')


class AccountCnPeriodClosing(models.Model):
    _name = 'account.cn.period.closing'
    _description = '期末结转损益'
    _order = 'date_to desc'

    name = fields.Char(string='名称', compute='_compute_name', store=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string='起始日期', required=True)
    date_to = fields.Date(string='截止日期', required=True)
    move_id = fields.Many2one(
        comodel_name='account.move', string='结转凭证', readonly=True, copy=False,
    )
    reversal_move_id = fields.Many2one(
        comodel_name='account.move', string='反结账凭证', readonly=True, copy=False,
    )
    state = fields.Selection(
        selection=[
            ('draft', '草稿'),
            ('posted', '已结转'),
            ('reversed', '已反结账'),
        ],
        string='状态', default='draft', required=True, readonly=True, copy=False,
    )

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for record in self:
            if record.date_from and record.date_to:
                record.name = _('%(date_from)s 至 %(date_to)s 期末结转') % {
                    'date_from': record.date_from,
                    'date_to': record.date_to,
                }
            else:
                record.name = _('期末结转')

    @api.constrains('date_from', 'date_to', 'company_id', 'state')
    def _check_no_overlap(self):
        for record in self:
            if record.state == 'reversed':
                continue
            overlapping = self.search_count([
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id),
                ('state', '!=', 'reversed'),
                ('date_from', '<=', record.date_to),
                ('date_to', '>=', record.date_from),
            ])
            if overlapping:
                raise ValidationError(_('该公司在此期间内已存在有效的结转记录，请勿重复结转。'))

    def _get_closing_journal(self):
        self.ensure_one()
        journal = self.env['account.journal'].search([
            ('company_id', '=', self.company_id.id),
            ('is_period_closing', '=', True),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].create({
                'name': _('期末结转'),
                'code': 'CLOSE',
                'type': 'general',
                'company_id': self.company_id.id,
                'is_period_closing': True,
            })
        return journal

    def action_generate(self):
        for record in self:
            if record.move_id:
                raise UserError(_('已生成过结转凭证，请勿重复生成。'))
            record._generate_move()

    def _generate_move(self):
        self.ensure_one()
        company = self.company_id
        domain = [
            ('parent_state', '=', 'posted'),
            ('company_id', '=', company.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('account_id.internal_group', 'in', _PL_INTERNAL_GROUPS),
        ]
        grouped = self.env['account.move.line']._read_group(
            domain, ['account_id'], ['debit:sum', 'credit:sum'],
        )

        line_vals = []
        net_balance = 0.0  # 借-贷 口径：损益类科目净额，负数代表净利润、正数代表净亏损
        for account, debit_sum, credit_sum in grouped:
            balance = debit_sum - credit_sum
            if company.currency_id.is_zero(balance):
                continue
            net_balance += balance
            line_vals.append(Command.create({
                'account_id': account.id,
                'debit': -balance if balance < 0 else 0.0,
                'credit': balance if balance > 0 else 0.0,
                'name': self.name,
            }))

        if not line_vals:
            raise UserError(_('所选期间内没有需要结转的损益类科目发生额。'))

        unaffected_account = company.get_unaffected_earnings_account()
        line_vals.append(Command.create({
            'account_id': unaffected_account.id,
            'debit': net_balance if net_balance > 0 else 0.0,
            'credit': -net_balance if net_balance < 0 else 0.0,
            'name': self.name,
        }))

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self._get_closing_journal().id,
            'company_id': company.id,
            'date': self.date_to,
            'ref': self.name,
            'line_ids': line_vals,
        })
        self.move_id = move.id

    def action_post(self):
        for record in self:
            if not record.move_id:
                raise UserError(_('请先生成结转凭证。'))
            if record.state != 'draft':
                raise UserError(_('只有草稿状态的结转记录才能过账。'))
            record.move_id.with_context(disable_abnormal_invoice_detection=True).action_post()
            record.state = 'posted'

    def action_advance_lock_date(self):
        for record in self:
            if record.state != 'posted':
                raise UserError(_('只有已结转的记录才能顺延锁账日期。'))
            company = record.company_id
            if not company.fiscalyear_lock_date or company.fiscalyear_lock_date < record.date_to:
                company.write({'fiscalyear_lock_date': record.date_to})

    def action_reverse(self):
        for record in self:
            if record.state != 'posted':
                raise UserError(_('只有已结转的记录才能反结账。'))
            reversal = record.move_id._reverse_moves(default_values_list=[{
                'date': record.move_id.date,
                'ref': _('反结转：%s') % record.name,
            }])
            reversal.with_context(disable_abnormal_invoice_detection=True).action_post()
            record.reversal_move_id = reversal.id
            record.state = 'reversed'

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('只有草稿状态的结转记录才能删除。'))
            if record.move_id:
                record.move_id.unlink()
        return super().unlink()
