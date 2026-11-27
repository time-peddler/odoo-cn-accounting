# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        if self.env.company.cn_credit_limit_hard_block:
            if not self.env.user.has_group('account_cn_credit_control.group_cn_credit_limit_override'):
                over_limit = self.filtered(lambda o: o.partner_credit_warning)
                if over_limit:
                    raise UserError(_(
                        '以下客户已超出信用额度，无法确认订单，请联系信用超限审批人处理：%s'
                    ) % '、'.join(over_limit.mapped('name')))
        return super().action_confirm()
