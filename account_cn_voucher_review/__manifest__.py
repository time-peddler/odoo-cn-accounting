# -*- coding: utf-8 -*-
{
    'name': '凭证审核',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '记账凭证的制单人/审核人分离（对标金蝶、用友的凭证审核机制）',
    'description': """
凭证审核
========

Odoo 核心自带的"Reviewed"勾选（`checked` 字段）是过账之后的展示性自评标记，
`_is_user_able_to_review()` 在核心里恒为真，没有任何真正的访问控制，也不会
阻止未经复核的凭证过账。

本模块参照金蝶、用友等主流财务软件的凭证审核机制，新增一道**过账之前**的
关卡：

- 制单人不能审核自己制作的凭证（可由公司整体政策放宽）
- 记账凭证（杂项/转账类日记账，按日记账可选开启）未经审核不能过账
- 审核后的凭证内容被锁定，需要先反审核才能修改
- 凭证一旦被重置为草稿，审核状态自动清空，必须重新审核才能再次过账
- 支持列表页多选批量审核/反审核

只作用于"记账凭证"（杂项分录），不影响客户发票、供应商账单等已有各自
业务单据审批流的场景。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/account_cn_voucher_review_security.xml',
        'views/account_move_views.xml',
        'views/account_move_search_views.xml',
        'views/account_journal_views.xml',
        'views/res_company_views.xml',
        'data/account_journal_cn_review_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
