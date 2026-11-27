# -*- coding: utf-8 -*-
{
    'name': '资金计划与现金流预测',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '汇总应收应付到期、票据到期、贷款还款计划的未来资金收支预测表',
    'description': """
资金计划与现金流预测
====================

`account_cn_statements` 的现金流量项目维度（`cn_cash_flow_item_id`）取数
方法硬编码围绕已过账的 `account.move.line`，没有抽象层可以扩展到未来、
尚未过账的数据，勉强改造反而会破坏那套引擎的简单性。

本模块原创实现一份独立的、面向未来的资金收支预测表：汇总应收应付账款的
到期日（Core 已有的 `date_maturity`）、票据到期日（若安装了
`account_cn_bill`）、贷款下一期还款计划（若安装了 `account_cn_loan`），
按周/月分桶展示预计流入/流出/净额。与三大报表/现金流量表完全独立，不
依赖也不影响那套引擎。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_cn_cash_forecast_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_cn_cash_forecast/static/src/cash_forecast/*.js',
            'account_cn_cash_forecast/static/src/cash_forecast/*.xml',
            'account_cn_cash_forecast/static/src/cash_forecast/*.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
