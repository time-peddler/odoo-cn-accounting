# -*- coding: utf-8 -*-
{
    'name': '期末结转损益',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '按会计期间生成、过账并可反结账的损益结转凭证（结转至本年利润）',
    'description': """
期末结转损益
============

Odoo 核心只是在生成报表时"动态"把损益类科目余额计入"本年利润"，从未产生一张
真正过账的结转凭证；而中国记账习惯要求每个会计期间都要有一张实际存在的
"结转损益"凭证，把当期损益类科目发生额清零，差额转入本年利润科目。

本模块新增"期末结转损益"记录：
- 按科目自动生成等额反向分录，将期间内全部损益类科目本期发生额结平
- 差额自动转入公司"本年利润"科目（复用 Odoo 核心的 `get_unaffected_earnings_account`）
- 生成的分录挂在专用的"期末结转"日记账下，过账前可正常审阅/修改
- 支持反结账（红字冲销），并可选择性顺延公司结账日期（复用 Odoo 核心已有的
  会计期间锁账机制，不重新实现锁账逻辑）
- 与 `account_cn_statements` 报表引擎联动：结转凭证自动从利润表"本期发生额"
  取数中排除，避免利润表被结转凭证自身重复冲抵
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account', 'account_cn_statements'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_cn_period_closing_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
