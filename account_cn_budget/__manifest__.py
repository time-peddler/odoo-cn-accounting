# -*- coding: utf-8 -*-
{
    'name': '全面预算管理',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '按科目编码+辅助核算维度编制预算，两态审批，并对采购订单/费用报销做超预算硬拦截',
    'description': """
全面预算管理
============

Odoo 社区版没有任何预算功能；企业版 account_budget 虽然可以编制预算，
但审批是假的（任何会计人员都能自行"确认/完成"，没有编制人/审批人分离），
超预算的采购订单也只做提示，不做硬拦截。

本模块原创实现：

- 预算按"科目编码前缀 + 可选辅助核算维度（部门/项目/员工等）+ 日期区间"
  编制，取数复用 Odoo 核心的 account.analytic.line（分析明细），
  已发生/已占用/剩余可用金额均为动态计算，不需要另外的结转逻辑
- 两态审批：编制中 → 待审批 → 已审批，且编制人不能审批本人编制的预算
  （复用本套件 account_cn_voucher_review 已验证的内控模式）
- 已审批预算可对采购订单确认、费用报销审批做硬拦截：公司开启开关后，
  超出预算余额的单据无法继续，只有"预算超支审批人"用户组成员可以放行
  （复用本套件 account_cn_credit_control 已验证的硬拦截模式）
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account', 'analytic', 'purchase', 'hr_expense'],
    'data': [
        'security/account_cn_budget_security.xml',
        'security/ir.model.access.csv',
        'views/account_cn_budget_views.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
