# -*- coding: utf-8 -*-
{
    'name': '中国会计准则动态财务报表',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '资产负债表、利润表、现金流量表的动态网页报表（企业会计准则）',
    'description': """
中国会计准则动态财务报表
========================

面向中国大陆企业会计准则的三大财务报表，以网页方式实时计算展示，
不依赖 PDF 导出：

- 资产负债表
- 利润表
- 现金流量表（直接法）

报表行项目按会计科目编码前缀取数，兼容标准的四位数字科目编码习惯
（与用友、金蝶等主流财务软件的编码方式一致），无需重新设计科目表。
现金流量表额外提供"现金流量项目"辅助核算维度，用于对银行/现金类
分录逐笔打标，从而按经营/投资/筹资活动自动归集。

原创实现，仅在建模思路上参考了通用财务报表引擎的常见设计（行树、
表达式、期间对比），未照搬任何第三方源码。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_cn_cash_flow_item_data.xml',
        'data/account_cn_statement_balance_sheet_data.xml',
        'data/account_cn_statement_income_statement_data.xml',
        'data/account_cn_statement_cash_flow_data.xml',
        'data/account_cn_account_names_data.xml',
        'views/account_move_line_views.xml',
        'views/account_cn_statement_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_cn_statements/static/src/statement_report/*.js',
            'account_cn_statements/static/src/statement_report/*.xml',
            'account_cn_statements/static/src/statement_report/*.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
