# -*- coding: utf-8 -*-
{
    'name': '纳税调整/不可抵扣费用管理',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '按科目挂纳税调整类别，动态测算企业所得税汇算清缴的纳税调整增加额',
    'description': """
纳税调整/不可抵扣费用管理
==========================

参考企业版"Account Fiscal Report"（`account_fiscal_categories`）的架构思路
原创实现：纳税调整类别挂在科目（`account.account`）层面，不需要逐笔在分录
上打标签；覆盖业务招待费"实际发生额 60%、但不超过当年销售营业收入 0.5%"
这类双重限制规则。

新增一张动态网页报表（非 PDF）：按类别展示实际发生额/可扣除限额/纳税调整
增加额，点击金额可钻取明细分录。同时向 `account_cn_income_tax_prepayment`
模块提供一个累计调整金额的取数方法，用于该模块的季度预缴测算（软联动，
未安装本模块也不影响所得税预缴测算模块的使用，只是需要手工填写调整额）。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_cn_disallowed_expense_category_views.xml',
        'views/account_account_views.xml',
        'views/account_cn_disallowed_expense_report_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_cn_disallowed_expenses/static/src/disallowed_expense_report/*.js',
            'account_cn_disallowed_expenses/static/src/disallowed_expense_report/*.xml',
            'account_cn_disallowed_expenses/static/src/disallowed_expense_report/*.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
