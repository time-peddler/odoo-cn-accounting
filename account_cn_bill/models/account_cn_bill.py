# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountCnBill(models.Model):
    _name = 'account.cn.bill'
    _description = '票据'
    _inherit = ['mail.thread']
    _order = 'maturity_date'

    name = fields.Char(string='票据号码', required=True, tracking=True)
    bill_type = fields.Selection(
        selection=[('receivable', '应收票据'), ('payable', '应付票据')],
        string='票据类别', required=True, default='receivable', tracking=True,
    )
    note_type = fields.Selection(
        selection=[('bank_acceptance', '银行承兑汇票'), ('commercial_acceptance', '商业承兑汇票')],
        string='票据种类', required=True, default='bank_acceptance',
    )
    partner_id = fields.Many2one(comodel_name='res.partner', string='往来单位', required=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', string='币种')
    amount = fields.Monetary(string='票面金额', required=True, currency_field='currency_id')
    issue_date = fields.Date(string='出票日', required=True, default=fields.Date.context_today)
    maturity_date = fields.Date(string='到期日', required=True)
    drawee_info = fields.Char(string='承兑人/出票行')
    journal_id = fields.Many2one(
        comodel_name='account.journal', string='记账日记账', required=True,
        domain="[('type', '=', 'general')]",
    )
    bank_journal_id = fields.Many2one(
        comodel_name='account.journal', string='银行日记账',
        domain="[('type', 'in', ('bank', 'cash'))]",
        help='到期兑付/支付、贴现收款时使用。',
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move', string='冲抵的原始单据',
        help='收到/开出本票据时用于结清的客户发票或供应商账单，可留空（不核销任何单据，'
             '仅登记票据本身）。',
    )
    state = fields.Selection(
        selection=[
            ('draft', '草稿'),
            ('held', '持有中'),
            ('endorsed', '已背书'),
            ('discounted', '已贴现'),
            ('settled', '已收付'),
            ('dishonored', '已拒付'),
        ],
        string='状态', default='draft', required=True, tracking=True, copy=False,
    )
    move_id = fields.Many2one(comodel_name='account.move', string='初始分录', readonly=True, copy=False)
    settlement_move_id = fields.Many2one(comodel_name='account.move', string='结算分录', readonly=True, copy=False)
    dishonor_move_id = fields.Many2one(comodel_name='account.move', string='拒付冲回分录', readonly=True, copy=False)

    @api.constrains('issue_date', 'maturity_date')
    def _check_dates(self):
        for bill in self:
            if bill.issue_date and bill.maturity_date and bill.issue_date > bill.maturity_date:
                raise ValidationError(_('"%s"：出票日不能晚于到期日。') % bill.name)

    def _cn_note_account(self):
        self.ensure_one()
        company = self.company_id
        account = (
            company.cn_notes_receivable_account_id
            if self.bill_type == 'receivable' else company.cn_notes_payable_account_id
        )
        if not account:
            raise UserError(_('请先在公司设置里配置"应收/应付票据科目"。'))
        return account

    def _cn_offset_account(self):
        self.ensure_one()
        account = (
            self.partner_id.property_account_receivable_id
            if self.bill_type == 'receivable' else self.partner_id.property_account_payable_id
        )
        if not account:
            raise UserError(_('往来单位"%s"未配置应收/应付账款科目。') % self.partner_id.name)
        return account

    def _cn_create_move(self, date, ref, line_vals, journal=None):
        self.ensure_one()
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': (journal or self.journal_id).id,
            'company_id': self.company_id.id,
            'date': date,
            'partner_id': self.partner_id.id,
            'ref': ref,
            'line_ids': line_vals,
        })
        move.action_post()
        return move

    def action_confirm(self):
        for bill in self.filtered(lambda b: b.state == 'draft'):
            note_account = bill._cn_note_account()
            offset_account = bill._cn_offset_account()
            is_receivable = bill.bill_type == 'receivable'
            move = bill._cn_create_move(
                bill.issue_date,
                _('票据 %s') % bill.name,
                [
                    Command.create({
                        'account_id': note_account.id, 'partner_id': bill.partner_id.id,
                        'debit': bill.amount if is_receivable else 0.0,
                        'credit': 0.0 if is_receivable else bill.amount,
                        'name': bill.name,
                    }),
                    Command.create({
                        'account_id': offset_account.id, 'partner_id': bill.partner_id.id,
                        'debit': 0.0 if is_receivable else bill.amount,
                        'credit': bill.amount if is_receivable else 0.0,
                        'name': bill.name,
                    }),
                ],
            )
            bill.move_id = move.id
            if bill.invoice_ids:
                offset_line = move.line_ids.filtered(lambda l: l.account_id == offset_account)
                to_reconcile = offset_line
                for invoice in bill.invoice_ids:
                    to_reconcile |= invoice.line_ids.filtered(
                        lambda l: l.account_id == offset_account and not l.reconciled
                    )
                if len(to_reconcile) > 1:
                    to_reconcile.reconcile()
            bill.state = 'held'

    def action_collect(self):
        for bill in self.filtered(lambda b: b.bill_type == 'receivable' and b.state == 'held'):
            if not bill.bank_journal_id or not bill.bank_journal_id.default_account_id:
                raise UserError(_('"%s"：请先选择有默认科目的收款银行日记账。') % bill.name)
            note_account = bill._cn_note_account()
            move = bill._cn_create_move(
                fields.Date.context_today(bill),
                _('票据兑付：%s') % bill.name,
                [
                    Command.create({
                        'account_id': bill.bank_journal_id.default_account_id.id,
                        'debit': bill.amount, 'credit': 0.0, 'name': bill.name,
                    }),
                    Command.create({
                        'account_id': note_account.id,
                        'debit': 0.0, 'credit': bill.amount, 'name': bill.name,
                    }),
                ],
                journal=bill.bank_journal_id,
            )
            bill.write({'state': 'settled', 'settlement_move_id': move.id})

    def action_pay(self):
        for bill in self.filtered(lambda b: b.bill_type == 'payable' and b.state == 'held'):
            if not bill.bank_journal_id or not bill.bank_journal_id.default_account_id:
                raise UserError(_('"%s"：请先选择有默认科目的付款银行日记账。') % bill.name)
            note_account = bill._cn_note_account()
            move = bill._cn_create_move(
                fields.Date.context_today(bill),
                _('票据支付：%s') % bill.name,
                [
                    Command.create({
                        'account_id': note_account.id,
                        'debit': bill.amount, 'credit': 0.0, 'name': bill.name,
                    }),
                    Command.create({
                        'account_id': bill.bank_journal_id.default_account_id.id,
                        'debit': 0.0, 'credit': bill.amount, 'name': bill.name,
                    }),
                ],
                journal=bill.bank_journal_id,
            )
            bill.write({'state': 'settled', 'settlement_move_id': move.id})

    def action_dishonor(self):
        for bill in self.filtered(lambda b: b.state in ('discounted', 'endorsed') and b.settlement_move_id):
            reversal = bill.settlement_move_id._reverse_moves(default_values_list=[{
                'date': fields.Date.context_today(bill),
                'ref': _('票据拒付冲回：%s') % bill.name,
            }])
            reversal.action_post()
            bill.write({'state': 'held', 'dishonor_move_id': reversal.id})

    def action_open_endorse_wizard(self):
        self.ensure_one()
        if self.bill_type != 'receivable' or self.state != 'held':
            raise UserError(_('只有持有中的应收票据才能背书转让。'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('背书转让'),
            'res_model': 'account.cn.bill.endorse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_bill_id': self.id},
        }

    def action_open_discount_wizard(self):
        self.ensure_one()
        if self.bill_type != 'receivable' or self.state != 'held':
            raise UserError(_('只有持有中的应收票据才能贴现。'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('票据贴现'),
            'res_model': 'account.cn.bill.discount.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_bill_id': self.id},
        }
