# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    cn_requires_review = fields.Boolean(
        string='需要审核',
        help='开启后，该日记账下"记账凭证"（杂项分录）在过账前必须先经过审核。'
             '客户发票、供应商账单等其它单据类型不受此项影响。',
    )

    @api.onchange('type')
    def _onchange_type_cn_requires_review(self):
        # 新建"杂项/转账"类日记账时默认建议开启审核，用户仍可在保存前取消勾选。
        # 结转日记账（account_cn_period_close 若安装）走程序化 create()，不经过
        # onchange，不受影响。
        if self.type == 'general' and not self.cn_requires_review:
            self.cn_requires_review = True

    @api.model
    def _cn_enable_review_for_general_journals(self):
        """模块安装/升级时，把已存在的"杂项/转账"类日记账默认打开审核开关，
        否则本模块在没有任何人工配置的情况下不会对任何凭证生效。

        排除 `is_period_closing` 为真的日记账（`account_cn_period_close` 模块
        新增的字段，本模块不依赖它，因此用 `_fields` 动态判断字段是否存在，
        不能直接在 domain 里写死这个字段名）——期末结转凭证按设计默认不需要
        再走一道审核，避免每月结转都要多等一次审核。
        """
        domain = [('type', '=', 'general'), ('cn_requires_review', '=', False)]
        if 'is_period_closing' in self._fields:
            domain.append(('is_period_closing', '=', False))
        self.search(domain).write({'cn_requires_review': True})
