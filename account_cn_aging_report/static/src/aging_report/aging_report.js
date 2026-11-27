/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

function formatDate(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/**
 * 客户/供应商往来账龄分析表。通过 params.account_type 区分客户账龄
 * （asset_receivable）与供应商账龄（liability_payable），两者共用同一
 * 取数引擎与展示组件。
 */
export class AccountCnAgingReport extends Component {
    static template = "account_cn_aging_report.AgingReport";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.accountType = this.props.action?.params?.account_type || "asset_receivable";

        this.state = useState({
            asOfDate: formatDate(new Date()),
            bucketLabels: [],
            rows: [],
            totals: [],
            grandTotal: 0,
            loading: true,
        });

        onWillStart(() => this.loadReport());
    }

    get title() {
        return this.accountType === "liability_payable" ? "供应商账龄分析表" : "客户账龄分析表";
    }

    async loadReport() {
        this.state.loading = true;
        const data = await this.orm.call(
            "account.cn.aging.report",
            "get_report_data",
            [this.accountType, this.state.asOfDate],
        );
        this.state.bucketLabels = data.bucket_labels;
        this.state.rows = data.rows;
        this.state.totals = data.totals;
        this.state.grandTotal = data.grand_total;
        this.state.loading = false;
    }

    onDateChanged() {
        this.loadReport();
    }

    formatAmount(value) {
        if (!value) {
            return "";
        }
        return new Intl.NumberFormat("zh-CN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }

    onCellClick(row, bucketIndex) {
        const domain = row.drilldown_domains[bucketIndex];
        if (!row.buckets[bucketIndex]) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `${row.partner_name} - ${this.state.bucketLabels[bucketIndex]}`,
            res_model: "account.move.line",
            view_mode: "list,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
            target: "current",
        });
    }
}

registry.category("actions").add("account_cn_aging_report", AccountCnAgingReport);
