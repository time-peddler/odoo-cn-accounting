# -*- coding: utf-8 -*-
{
    'name': '银行对账单导入',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '通用列映射方式导入银行流水（CSV/Excel），生成待核销的银行日记账分录',
    'description': """
银行对账单导入
==============

企业版"通用导入框架 + 按格式插件化解析"（`account_bank_statement_import`）
本身就是依赖 `account_accountant` 的企业版专属能力：Community 没有
`account.journal._parse_bank_statement_file` 这个可插拔钩子，也没有对账
小部件/自动核销引擎，"给中国银行配一个解析器插件"这个设想没有插件宿主可插。

本模块改为原创一个更轻量、不依赖企业版机制的独立导入向导：把银行流水的
每一行直接解析成一张待人工核销的银行日记账分录（对方科目挂公司可配置的
"银行导入暂存"科目），核销通过 Community 原生的"日记账分录核销"操作完成，
不做智能自动核销、不做拖拽式对账小部件——这是由技术现状决定的范围收窄。

支持通用列映射（日期/摘要/收入/支出/对方户名），可按用户实际银行导出的
表头调整对应列，不假设任何特定银行的固定格式。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'wizard/account_cn_bank_import_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
