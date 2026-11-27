# -*- coding: utf-8 -*-
{
    'name': '会计辅助核算维度（部门/员工）',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '将部门、员工接入 Odoo 多维辅助核算体系，作为会计分录可选的分析维度',
    'description': """
会计辅助核算维度（部门/员工）
==============================

Odoo 核心的多维辅助核算体系（`account.analytic.plan`）本身已支持任意自定义
维度，"项目"维度已经与 `project.project` 打通，但"部门""员工"这两个中国财务
软件里最常用的辅助核算维度一直没有对应的分析核算档案。

本模块新增"部门""员工"两个辅助核算维度（`account.analytic.plan`），并让
`hr.department`/`hr.employee` 在创建时自动生成/同步对应的分析账户
（`account.analytic.account`），此后即可在任意会计分录的"分析明细"
（`analytic_distribution`）里按部门或员工进行核算，无需改动任何记账界面。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account', 'analytic', 'hr'],
    'data': [
        'data/account_analytic_plan_data.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
