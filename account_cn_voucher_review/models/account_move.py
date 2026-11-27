# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# 已审核但尚未过账的凭证，禁止直接修改这些会影响记账内容的字段，
# 需要先反审核。审核状态自身的字段（cn_review_state 等）不在此列，
# 否则我们自己的审核/反审核方法都会被这条规则挡住。
_CN_PROTECTED_FIELDS = {'line_ids', 'date', 'journal_id', 'partner_id', 'currency_id', 'ref'}


class AccountMove(models.Model):
    _inherit = 'account.move'

    cn_review_state = fields.Selection(
        selection=[
            ('to_review', '待审核'),
            ('reviewed', '已审核'),
        ],
        string='审核状态', default='to_review', copy=False, tracking=True,
    )
    cn_reviewed_by = fields.Many2one(
        comodel_name='res.users', string='审核人', readonly=True, copy=False, tracking=True,
    )
    cn_reviewed_date = fields.Datetime(
        string='审核时间', readonly=True, copy=False, tracking=True,
    )
    cn_review_required = fields.Boolean(
        string='需要审核', compute='_compute_cn_review_required', store=True,
        help='供界面按钮/列显示及列表页筛选使用（需要 store=True 才能搜索），'
             '业务判断请调用 _cn_requires_review()。',
    )

    @api.depends('company_id.cn_voucher_review_enabled', 'journal_id.cn_requires_review', 'move_type')
    def _compute_cn_review_required(self):
        for move in self:
            move.cn_review_required = move._cn_requires_review()

    def _cn_requires_review(self):
        # 刻意只审核 move_type == 'entry'（记账凭证），不含发票/账单——已与
        # 用户确认：金蝶/用友对所有入总账凭证一视同仁地审核，但 Odoo 的
        # "过账发票"同时承担确认业务单据的作用，纳入审核会拖慢开票流程，
        # 因此收窄范围是产品决策而非遗漏。如需扩大范围，去掉下面
        # move_type 这一条件即可，其余逻辑不用改。
        self.ensure_one()
        return bool(
            self.company_id.cn_voucher_review_enabled
            and self.journal_id.cn_requires_review
            and self.move_type == 'entry'
        )

    def _cn_move_label(self):
        """凭证在过账前 name 字段通常还是 False（要过账时才由序列生成），
        拼错误提示信息时不能直接假设 name 一定是字符串。"""
        self.ensure_one()
        return self.name or _('草稿凭证 #%s') % self.id

    def action_cn_review(self):
        if not self.env.user.has_group('account_cn_voucher_review.group_cn_voucher_reviewer'):
            raise UserError(_('你没有凭证审核权限。'))

        to_review = self.filtered(
            lambda m: m._cn_requires_review() and m.cn_review_state != 'reviewed'
        )
        if not to_review:
            return

        # 按每张凭证自己所属公司的政策判断，避免多公司批量审核时
        # 误用当前登录用户的活动公司设置去套用到其它公司的凭证上
        self_made = to_review.filtered(
            lambda m: m.create_uid.id == self.env.uid and not m.company_id.cn_voucher_review_allow_self
        )
        if self_made:
            raise UserError(_(
                '制单人不能审核本人制作的凭证：%s'
            ) % '、'.join(m._cn_move_label() for m in self_made))

        to_review.write({
            'cn_review_state': 'reviewed',
            'cn_reviewed_by': self.env.uid,
            'cn_reviewed_date': fields.Datetime.now(),
        })

    def action_cn_unreview(self):
        if not self.env.user.has_group('account_cn_voucher_review.group_cn_voucher_reviewer'):
            raise UserError(_('你没有凭证审核权限。'))

        not_draft = self.filtered(lambda m: m.cn_review_state == 'reviewed' and m.state != 'draft')
        if not_draft:
            raise UserError(_(
                '已过账的凭证不能直接反审核，请先将其重置为草稿：%s'
            ) % '、'.join(m._cn_move_label() for m in not_draft))

        self.filtered(lambda m: m.cn_review_state == 'reviewed').write({
            'cn_review_state': 'to_review',
            'cn_reviewed_by': False,
            'cn_reviewed_date': False,
        })

    def action_post(self):
        blocked = self.filtered(
            lambda m: m._cn_requires_review() and m.cn_review_state != 'reviewed'
        )
        if blocked:
            raise UserError(_(
                '以下凭证尚未审核，不能过账：%s'
            ) % '、'.join(m._cn_move_label() for m in blocked))
        return super().action_post()

    def button_draft(self):
        res = super().button_draft()
        self.filtered(lambda m: m.cn_review_state == 'reviewed').write({
            'cn_review_state': 'to_review',
            'cn_reviewed_by': False,
            'cn_reviewed_date': False,
        })
        return res

    def write(self, vals):
        if _CN_PROTECTED_FIELDS.intersection(vals):
            locked = self.filtered(lambda m: m.state == 'draft' and m.cn_review_state == 'reviewed')
            if locked:
                raise UserError(_(
                    '以下凭证已审核，内容已锁定，请先反审核再修改：%s'
                ) % '、'.join(m._cn_move_label() for m in locked))
        return super().write(vals)
