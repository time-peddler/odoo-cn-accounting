# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountCnLoanRepaymentLine(models.Model):
    _name = 'account.cn.loan.repayment.line'
    _description = '借款还款计提明细'
    _order = 'period_date'

    loan_id = fields.Many2one(comodel_name='account.cn.loan', string='借款', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='loan_id.currency_id', string='币种')
    period_date = fields.Date(string='计提日期', required=True)
    principal_amount = fields.Monetary(string='本金', currency_field='currency_id')
    interest_amount = fields.Monetary(string='利息', currency_field='currency_id')
    move_id = fields.Many2one(comodel_name='account.move', string='凭证', readonly=True)
    state = fields.Selection(
        selection=[('draft', '草稿'), ('posted', '已过账')],
        string='状态', default='draft', required=True,
    )
