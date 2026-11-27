# -*- coding: utf-8 -*-
from odoo import Command, _, fields, models
from odoo.exceptions import UserError


class AccountCnBillEndorseWizard(models.TransientModel):
    _name = 'account.cn.bill.endorse.wizard'
    _description = '票据背书转让'

    bill_id = fields.Many2one(comodel_name='account.cn.bill', string='票据', required=True)
    endorse_date = fields.Date(string='背书日期', required=True, default=fields.Date.context_today)
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='背书受让方（供应商）', required=True,
        help='用本票据冲抵本公司对该供应商的应付账款。',
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move', string='冲抵的供应商账单',
        help='可留空，留空则只做账，不核销任何具体账单。',
    )

    def action_confirm(self):
        self.ensure_one()
        bill = self.bill_id
        note_account = bill._cn_note_account()
        payable_account = self.partner_id.property_account_payable_id
        if not payable_account:
            raise UserError(_('往来单位"%s"未配置应付账款科目。') % self.partner_id.name)

        move = bill._cn_create_move(
            self.endorse_date, _('票据背书转让：%s') % bill.name,
            [
                Command.create({
                    'account_id': payable_account.id, 'partner_id': self.partner_id.id,
                    'debit': bill.amount, 'credit': 0.0, 'name': bill.name,
                }),
                Command.create({
                    'account_id': note_account.id, 'partner_id': self.partner_id.id,
                    'debit': 0.0, 'credit': bill.amount, 'name': bill.name,
                }),
            ],
        )
        if self.invoice_ids:
            payable_line = move.line_ids.filtered(lambda l: l.account_id == payable_account)
            to_reconcile = payable_line
            for invoice in self.invoice_ids:
                to_reconcile |= invoice.line_ids.filtered(
                    lambda l: l.account_id == payable_account and not l.reconciled
                )
            if len(to_reconcile) > 1:
                to_reconcile.reconcile()
        bill.write({'state': 'endorsed', 'settlement_move_id': move.id})
