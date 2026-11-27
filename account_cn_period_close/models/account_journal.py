# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_period_closing = fields.Boolean(
        string='用于期末结转',
        copy=False,
        help='标记为期末结转专用日记账后，该日记账下的分录会被中国会计准则动态'
             '财务报表的利润表取数逻辑自动排除，避免结转凭证重复计入当期发生额。',
    )
