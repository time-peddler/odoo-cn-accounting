# -*- coding: utf-8 -*-
{
    'name': '借款管理',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '短期/长期借款登记，三种还款方式的本息拆分与批量计提还本付息',
    'description': """
借款管理
========

原创实现，三种法定还款方式（等额本金/等额本息/先息后本）均按月计提。折旧式
"现算下一期"设计（与本套件 account_cn_asset 的固定资产折旧引擎同构）：不
预生成整张还款排期表，提前还款/状态变化后下一期自动按新的剩余本金重新计算，
不需要"作废重排"——这一点上不采用企业版 account_loans 的"预生成整张排期表"
做法，延续本套件自己的既有约定。

长期借款"一年内到期部分"重分类为可选功能（企业会计准则要求，但标准 l10n_cn
科目表没有"一年内到期的非流动负债"科目，只有大企业科目表 cn_large_bis 才有）：
配置了对应科目才会执行，做法借鉴企业版 account_loans 的"月末重分类 + 次日
自动红冲"技巧，未配置则整段逻辑跳过，不强制要求。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_cn_loan_views.xml',
        'wizard/account_cn_loan_repayment_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
