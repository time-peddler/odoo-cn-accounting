# -*- coding: utf-8 -*-
{
    'name': '增值税及附加税费申报',
    'version': '19.0.1.0.0',
    'category': '会计/中国本地化报表',
    'summary': '按期编制增值税及附加税费申报表，自动结转期初/期末留抵税额',
    'description': """
增值税及附加税费申报
====================

`l10n_cn` 科目表虽然预置了应交增值税的一整套二级科目（销项税额/进项税额/
进项税额转出等），但开票/记账时税额全部计入顶层"应交税费"科目，二级科目
并未被任何税率自动分流。本模块采用"双轨"取数策略，不修改 `l10n_cn` 任何
数据：

- 销项税额/进项税额：直接按 `account.move.line.tax_line_id` 的
  `type_tax_use`（销项/进项）取数，不依赖科目
- 进项税额转出等手工调整分录：按科目编码前缀（如 2221.01.04）取数，这类
  调整本来就是财务手工记到对应二级科目的过渡性分录

新增"增值税及附加税费申报表"：一期一条记录，编制中可反复重新生成，确认
后数值定案；期初留抵税额自动从上一期已确认记录的期末留抵结转；同时按公司
可配置的税率自动算出城建税/教育费附加/地方教育费附加。
    """,
    'author': 'luckin',
    'website': 'https://github.com/time-peddler/odoo-cn-accounting',
    'license': 'AGPL-3',
    'depends': ['account', 'l10n_cn'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_cn_vat_return_views.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
