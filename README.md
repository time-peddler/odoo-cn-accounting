# Odoo CN Accounting

**面向 Odoo 19 的中国财务本地化套件 | Chinese accounting and finance extensions for Odoo 19**

[![Odoo 19](https://img.shields.io/badge/Odoo-19.0-714B67)](https://www.odoo.com/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

本项目为 Odoo 提供面向中国企业财务管理实践的模块化扩展，覆盖财务报表、凭证审核、期末结账、资产、资金、预算及税务测算等场景。可按业务需求选择安装，不替代 Odoo 官方中国会计本地化模块 `l10n_cn`。

## 功能模块

| 技术名称 | 功能 |
| --- | --- |
| `account_cn_aging_report` | 往来账龄分析表：客户/供应商往来账龄分析表，按标准账龄区间动态展示（网页方式，非 PDF） |
| `account_cn_analytic_dimensions` | 会计辅助核算维度（部门/员工）：将部门、员工接入 Odoo 多维辅助核算体系，作为会计分录可选的分析维度 |
| `account_cn_asset` | 固定资产管理：中国企业会计准则下的固定资产全生命周期管理：四种法定折旧方法、调拨、减值、盘点、处置清理 |
| `account_cn_bank_import` | 银行对账单导入：通用列映射方式导入银行流水（CSV/Excel），生成待核销的银行日记账分录 |
| `account_cn_bill` | 票据管理：应收/应付票据（银行承兑汇票、商业承兑汇票）全生命周期管理 |
| `account_cn_budget` | 全面预算管理：按科目编码+辅助核算维度编制预算，两态审批，并对采购订单/费用报销做超预算硬拦截 |
| `account_cn_cash_forecast` | 资金计划与现金流预测：汇总应收应付到期、票据到期、贷款还款计划的未来资金收支预测表 |
| `account_cn_credit_control` | 客户信用管理：在销售订单确认与客户发票过账前，对超出信用额度的客户做硬性拦截 |
| `account_cn_disallowed_expenses` | 纳税调整/不可抵扣费用管理：按科目挂纳税调整类别，动态测算企业所得税汇算清缴的纳税调整增加额 |
| `account_cn_dunning` | 客户催款管理：按逾期天数分级的多级催款提醒（邮件通知客户，企业微信内部提醒销售员） |
| `account_cn_income_tax_prepayment` | 企业所得税季度预缴测算：按季度累计利润总额测算企业所得税预缴额，自动结转以前季度已预缴数 |
| `account_cn_loan` | 借款管理：短期/长期借款登记，三种还款方式的本息拆分与批量计提还本付息 |
| `account_cn_period_close` | 期末结转损益：按会计期间生成、过账并可反结账的损益结转凭证（结转至本年利润） |
| `account_cn_statements` | 中国会计准则动态财务报表：资产负债表、利润表、现金流量表的动态网页报表（企业会计准则） |
| `account_cn_tax_return` | 增值税及附加税费申报：按期编制增值税及附加税费申报表，自动结转期初/期末留抵税额 |
| `account_cn_voucher_review` | 凭证审核：记账凭证的制单人/审核人分离（对标金蝶、用友的凭证审核机制） |

## 环境与依赖

- Odoo 19.0（模块清单声明版本为 19.0.1.0.0）。
- PostgreSQL：使用与 Odoo 19 兼容的数据库版本，例如 PostgreSQL 16。
- Python：使用 Odoo 19 自身的运行环境；Excel 导入需要 `openpyxl`。
- 根据所选模块，安装 Odoo 自带的 `account`、`l10n_cn`、`analytic`、`hr`、`purchase`、`hr_expense`、`sale` 等依赖。期末结转依赖本仓库的财务报表模块。
- 催款的企业微信通知为可选集成，需要环境另行提供兼容的 `wechat.notification.service`；本仓库不包含该服务。标准邮件通知不依赖它。

## 安装

1. 克隆仓库：

   ```bash
   git clone https://github.com/time-peddler/odoo-cn-accounting.git
   ```

2. 将仓库根目录加入 Odoo 的 `addons_path`（保留原有官方和自定义 addons 路径）。Docker 部署时可将仓库挂载到未被占用的容器目录，例如：

   ```yaml
   services:
     odoo:
       volumes:
         - ./odoo-cn-accounting:/mnt/extra-addons/odoo-cn-accounting:ro
   ```

   并在 Odoo 配置的 addons_path 中加入 `/mnt/extra-addons/odoo-cn-accounting`。这是现有 Compose 配置的增量示例，不是完整部署文件。

3. 如环境尚未提供 `openpyxl`，在 Odoo Python 环境中安装（容器部署推荐在自定义镜像构建阶段安装）。
4. 在独立测试数据库启用开发者模式，更新应用列表，取消默认的“应用”筛选，搜索模块技术名称并按需安装。
5. 也可使用 Odoo CLI，在已正确配置数据库连接和 addons_path 的环境中安装指定模块：

   ```bash
   odoo -c /etc/odoo/odoo.conf -d test_accounting \
     -i l10n_cn,account_cn_statements,account_cn_voucher_review \
     --stop-after-init --no-http
   ```

   请根据实际部署调整配置路径、数据库名称和运行命令。

## 使用建议

- 先配置公司、会计科目、会计日记账、币种和中国本地化科目表。
- 根据企业会计制度配置报表取数规则、现金流量项目、辅助核算维度和审核权限。
- 财务报表模块安装或升级时会调用标准科目名称更新逻辑；请在测试库验证与已有科目表的兼容性。
- 预算和信用控制可影响采购、报销、销售确认或发票过账；启用前先验证业务规则。
- 催款模块包含定时任务，配置外发邮件前请先使用测试邮箱并检查任务权限。
- 固定资产折旧、税务测算、期末结转及财务报表应由财务人员使用实际会计政策核对。

## 项目状态

本仓库为初始开源版本。发布前已在隔离的 Odoo 19.0-20260817 / PostgreSQL 16 环境中验证 16 个模块同时安装成功；尚未完成全面的业务回归测试、权限审计或财务数据核验，暂不承诺生产环境适用性，也不保证所有中国会计或税务规则均已覆盖。安装前备份数据库，在隔离环境验证模块安装、权限、跨公司数据隔离、报表和会计分录准确性。本项目不提供税务申报直连或官方合规认证。

## 贡献与反馈

欢迎通过 GitHub Issues 提交可复现的问题、功能建议或兼容性反馈，或通过 Pull Request 提交修复。请勿上传真实账套、客户信息、银行流水、税号或访问凭据；使用虚构测试数据。

## License

GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE).

Odoo and its official modules are separate projects with their own licenses. This repository is an independent extension and is not affiliated with or endorsed by Odoo S.A.

## English overview

Odoo CN Accounting is a modular suite for Chinese accounting workflows on Odoo 19, including financial statements, voucher review, period closing, assets, budgets, bills, bank statement imports, loans, cash forecasting, credit control, dunning and tax calculations. Install only the addons you need and validate the results against your accounting policies in a test database before production use.
