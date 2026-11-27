# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        if self.env.company.cn_credit_limit_hard_block:
            if not self.env.user.has_group('account_cn_credit_control.group_cn_credit_limit_override'):
                over_limit = self.filtered(
                    lambda m: m.move_type == 'out_invoice' and m.partner_credit_warning
                )
                if over_limit:
                    raise UserError(_(
                        '以下客户已超出信用额度，无法过账发票，请联系信用超限审批人处理：%s'
                    ) % '、'.join(m.name or _('草稿发票 #%s') % m.id for m in over_limit))
        return super().action_post()
