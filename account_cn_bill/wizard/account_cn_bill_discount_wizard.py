# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountCnBillDiscountWizard(models.TransientModel):
    _name = 'account.cn.bill.discount.wizard'
    _description = '票据贴现'

    bill_id = fields.Many2one(comodel_name='account.cn.bill', string='票据', required=True)
    currency_id = fields.Many2one(related='bill_id.currency_id', string='币种')
    discount_date = fields.Date(string='贴现日期', required=True, default=fields.Date.context_today)
    discount_interest = fields.Monetary(string='贴现利息', required=True, currency_field='currency_id')
    bank_journal_id = fields.Many2one(
        comodel_name='account.journal', string='收款银行日记账', required=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
    )
    treatment = fields.Selection(
        selection=[('derecognize', '出表法（终止确认应收票据）'), ('financing', '融资法（应收票据留账，计入短期借款）')],
        string='贴现处理方式', required=True,
    )
    net_proceeds = fields.Monetary(
        string='实收金额', compute='_compute_net_proceeds', currency_field='currency_id',
    )

    @api.onchange('bill_id')
    def _onchange_bill_id(self):
        if self.bill_id:
            self.treatment = (
                'derecognize' if self.bill_id.note_type == 'bank_acceptance' else 'financing'
            )

    @api.depends('bill_id.amount', 'discount_interest')
    def _compute_net_proceeds(self):
        for wizard in self:
            wizard.net_proceeds = (wizard.bill_id.amount or 0.0) - wizard.discount_interest

    def action_confirm(self):
        self.ensure_one()
        bill = self.bill_id
        company = bill.company_id
        if not self.bank_journal_id.default_account_id:
            raise UserError(_('所选银行日记账未配置默认科目。'))
        if not company.cn_bill_interest_expense_account_id:
            raise UserError(_('请先在公司设置里配置"票据贴现利息费用科目"。'))
        if self.discount_interest < 0 or self.discount_interest > bill.amount:
            raise UserError(_('贴现利息应在 0 与票面金额之间。'))

        note_account = bill._cn_note_account()
        if self.treatment == 'derecognize':
            credit_account = note_account
        else:
            if not company.cn_bill_financing_account_id:
                raise UserError(_('请先在公司设置里配置"票据贴现融资科目"。'))
            credit_account = company.cn_bill_financing_account_id

        line_vals = [
            Command.create({
                'account_id': self.bank_journal_id.default_account_id.id,
                'debit': self.net_proceeds, 'credit': 0.0, 'name': bill.name,
            }),
        ]
        if self.discount_interest:
            line_vals.append(Command.create({
                'account_id': company.cn_bill_interest_expense_account_id.id,
                'debit': self.discount_interest, 'credit': 0.0, 'name': _('%s 贴现利息') % bill.name,
            }))
        line_vals.append(Command.create({
            'account_id': credit_account.id,
            'debit': 0.0, 'credit': bill.amount, 'name': bill.name,
        }))

        move = bill._cn_create_move(
            self.discount_date, _('票据贴现：%s') % bill.name, line_vals, journal=self.bank_journal_id,
        )
        bill.write({'state': 'discounted', 'settlement_move_id': move.id})
