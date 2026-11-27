# -*- coding: utf-8 -*-
{
    'name': '客户催款管理',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '按逾期天数分级的多级催款提醒（邮件通知客户，企业微信内部提醒销售员）',
    'description': """
客户催款管理
============

参考主流财务软件"多级催收策略"的思路原创实现：按逾期天数配置若干个
催收等级（如"提醒""催告""最后通牒"），系统每日自动检查客户的应收账款，
一旦升级到新的催收等级就触发一次提醒，同一等级不会重复打扰客户。

催客户本人的提醒统一走 Odoo 标准邮件模板；如果本环境另行安装了兼容的
企业微信通知模块，同时可以在客户升级到某个等级时，内部提醒对应发票的
销售员——两条通道各司其职：**邮件面向客户，企业微信面向内部员工**（企业
微信应用消息本身无法直接发送给外部客户）。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/account_cn_dunning_level_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
