# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models


class AccountCnLoanRepaymentWizard(models.TransientModel):
    _name = 'account.cn.loan.repayment.wizard'
    _description = '批量计提还本付息'

    date = fields.Date(string='计提日期', required=True, default=fields.Date.context_today)
    line_ids = fields.One2many(
        comodel_name='account.cn.loan.repayment.wizard.line', inverse_name='wizard_id',
        string='本期还款明细',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'line_ids' in fields_list:
            loans = self.env['account.cn.loan'].search([
                ('state', '=', 'running'), ('company_id', '=', self.env.company.id),
            ])
            res['line_ids'] = [Command.create({'loan_id': loan.id}) for loan in loans]
        return res

    def action_confirm(self):
        self.ensure_one()
        for line in self.line_ids:
            loan = line.loan_id
            if not loan:
                continue
            principal, interest = loan._cn_compute_next_repayment()
            if loan.currency_id.is_zero(principal) and loan.currency_id.is_zero(interest):
                continue

            move_lines = []
            total = principal + interest
            if interest:
                move_lines.append(Command.create({
                    'account_id': loan.interest_expense_account_id.id,
                    'debit': interest, 'credit': 0.0, 'name': _('%s 利息') % loan.name,
                }))
            if principal:
                move_lines.append(Command.create({
                    'account_id': loan.loan_account_id.id,
                    'debit': principal, 'credit': 0.0, 'name': _('%s 本金') % loan.name,
                }))
            move_lines.append(Command.create({
                'account_id': loan.journal_id.default_account_id.id,
                'debit': 0.0, 'credit': total, 'name': loan.name,
            }))
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': loan.journal_id.id,
                'company_id': loan.company_id.id,
                'partner_id': loan.partner_id.id,
                'date': self.date,
                'ref': _('%(loan)s 还本付息 %(date)s') % {'loan': loan.name, 'date': self.date},
                'line_ids': move_lines,
            })
            move.action_post()
            self.env['account.cn.loan.repayment.line'].create({
                'loan_id': loan.id,
                'period_date': self.date,
                'principal_amount': principal,
                'interest_amount': interest,
                'move_id': move.id,
                'state': 'posted',
            })

            if loan.loan_type == 'long_term' and loan.current_portion_account_id:
                loan._cn_reclassify_current_portion(self.date)

        return {
            'type': 'ir.actions.act_window',
            'name': _('还本付息凭证'),
            'res_model': 'account.cn.loan.repayment.line',
            'view_mode': 'list,form',
            'domain': [('period_date', '=', self.date), ('loan_id', 'in', self.line_ids.loan_id.ids)],
        }


class AccountCnLoanRepaymentWizardLine(models.TransientModel):
    _name = 'account.cn.loan.repayment.wizard.line'
    _description = '批量计提还本付息-借款明细'

    wizard_id = fields.Many2one(comodel_name='account.cn.loan.repayment.wizard')
    loan_id = fields.Many2one(comodel_name='account.cn.loan', string='借款')
    currency_id = fields.Many2one(related='loan_id.currency_id', string='币种')
    repayment_method = fields.Selection(related='loan_id.repayment_method', string='还款方式')
    preview_principal = fields.Monetary(
        string='预计本金', compute='_compute_preview', currency_field='currency_id',
    )
    preview_interest = fields.Monetary(
        string='预计利息', compute='_compute_preview', currency_field='currency_id',
    )

    @api.depends('loan_id')
    def _compute_preview(self):
        for line in self:
            if line.loan_id:
                principal, interest = line.loan_id._cn_compute_next_repayment()
            else:
                principal, interest = 0.0, 0.0
            line.preview_principal = principal
            line.preview_interest = interest
