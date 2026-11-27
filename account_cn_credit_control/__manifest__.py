# -*- coding: utf-8 -*-
{
    'name': '客户信用管理',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '在销售订单确认与客户发票过账前，对超出信用额度的客户做硬性拦截',
    'description': """
客户信用管理
============

Odoo 核心已经有完整的信用额度基础设施（公司总开关、客户专属信用额度、
超额提示语的计算逻辑），但只会在单据表单顶部弹一条可以直接忽略的黄色
提示条，销售订单确认、客户发票过账都不会被真正拦下来。

本模块在此基础上补一道硬拦截：
- 公司可选择开启"信用超限强制拦截"
- 开启后，客户超出信用额度时，普通用户无法确认销售订单、无法过账客户发票
- "信用超限审批人"用户组的成员不受此限制，可以照常操作

不重新计算信用额度，直接复用 Odoo 核心已经算好的 `partner_credit_warning`。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account', 'sale'],
    'data': [
        'security/account_cn_credit_control_security.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
