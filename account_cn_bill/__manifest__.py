# -*- coding: utf-8 -*-
{
    'name': '票据管理',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '应收/应付票据（银行承兑汇票、商业承兑汇票）全生命周期管理',
    'description': """
票据管理
========

account_ref 中完全没有票据/汇票相关的模型或逻辑，本模块原创实现应收/应付
票据的登记、背书转让、贴现（出表法/融资法）、到期兑付/支付、拒付简化处理。

`l10n_cn` 的"应收票据"(1121)/"应付票据"(2201) 科目 `reconcile=False`，
核心的应收应付核销机制不适用于票据本身：本模块的做法是让票据结算分录里
冲销应收账款/应付账款的那一行（1122/2202，本身是可核销科目）去核销原发票，
不去动 1121/2201，不需要修改 l10n_cn 任何数据。

银行承兑汇票与商业承兑汇票因信用风险不同，贴现的会计处理也不同：银行承兑
默认按"出表法"（终止确认应收票据），商业承兑默认按"融资法"（应收票据留账，
贴现所得计入短期借款），两者均可在贴现时按需切换。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_cn_bill_data.xml',
        'views/account_cn_bill_views.xml',
        'views/res_company_views.xml',
        'wizard/account_cn_bill_discount_wizard_views.xml',
        'wizard/account_cn_bill_endorse_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
