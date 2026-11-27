# -*- coding: utf-8 -*-
{
    'name': '固定资产管理',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '中国企业会计准则下的固定资产全生命周期管理：四种法定折旧方法、调拨、减值、盘点、处置清理',
    'description': """
固定资产管理
============

Odoo 社区版没有任何固定资产折旧能力（该能力只在企业版提供）。本模块原创
实现面向中国企业会计准则的固定资产管理：

- 资产类别预置对应 l10n_cn 科目表的六个固定资产子类别（房屋建筑物/机器
  设备/运输设备/电子设备/办公设备/其他固定资产），自动匹配对应科目
- 四种法定折旧方法：年限平均法、工作量法、双倍余额递减法（最后两年强制
  转直线法）、年数总和法
- 资产变动全生命周期：新增、部门间调拨、计提减值（不可转回）、盘点
  盈亏（走"待处理财产损溢"过渡科目）、处置清理（走"固定资产清理"过渡
  科目，损益结转至"资产处置损益"）

参考社区模块 om_account_asset 的整体架构思路（类别-资产-折旧明细-向导
四层结构），但其折旧算法只覆盖"年限平均法"一种，双倍余额递减法/年数
总和法/工作量法均为原创实现；处置清理流程也未采用其"直接补提折旧"的
简化处理，改为原创的"固定资产清理"过渡科目完整流程，更贴合国内实务。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_cn_asset_category_data.xml',
        'views/account_cn_asset_category_views.xml',
        'views/account_cn_asset_views.xml',
        'views/account_cn_asset_transfer_views.xml',
        'views/account_cn_asset_impairment_views.xml',
        'views/account_cn_asset_inventory_count_views.xml',
        'wizard/account_cn_asset_depreciation_wizard_views.xml',
        'wizard/account_cn_asset_disposal_wizard_views.xml',
        'views/account_cn_asset_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
