# -*- coding: utf-8 -*-
{
    'name': '往来账龄分析表',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '客户/供应商往来账龄分析表，按标准账龄区间动态展示（网页方式，非 PDF）',
    'description': """
往来账龄分析表
==============

Odoo 核心只提供每个客户/供应商的应收/应付"合计单一数字"（`res.partner.credit`/
`debit`），没有任何按到期日分账龄区间展示的报表，Enterprise 的账龄报表模块
（account_reports）也不在本地环境里。

本模块原创实现一张"客户/供应商 × 账龄区间"的动态网页报表：
- 账龄区间沿用用友、金蝶通用的标准分段：未到期 / 1-30 天 / 31-60 天 /
  61-90 天 / 90 天以上
- 按截止日期实时计算，点击金额可钻取到明细分录
- 客户账龄、供应商账龄共用同一套取数引擎，通过参数区分
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_cn_aging_report_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_cn_aging_report/static/src/aging_report/*.js',
            'account_cn_aging_report/static/src/aging_report/*.xml',
            'account_cn_aging_report/static/src/aging_report/*.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
