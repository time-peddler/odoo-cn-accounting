# -*- coding: utf-8 -*-
{
    'name': '企业所得税季度预缴测算',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '按季度累计利润总额测算企业所得税预缴额，自动结转以前季度已预缴数',
    'description': """
企业所得税季度预缴测算
======================

原创实现企业所得税季度预缴测算："利润总额"（年初至今累计数）独立按科目
类型对 account.move.line 求和取数，不依赖 account_cn_statements 模块；
"纳税调整增加额"在安装 account_cn_disallowed_expenses 模块时自动联动取数，
未安装则手工填写。

已知局限（第一版范围内不做）：不处理"弥补以前年度亏损"的自动结转台账，
提供一个手工填写字段由用户按税务口径自行填报；不做小型微利企业等分级
优惠税率的自动判定，税率由公司自行配置。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_cn_income_tax_prepayment_views.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
