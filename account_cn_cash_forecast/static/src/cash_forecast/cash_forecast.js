/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

function formatDate(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function addMonths(date, months) {
    return new Date(date.getFullYear(), date.getMonth() + months, date.getDate());
}

/**
 * 资金计划与现金流预测：汇总应收应付到期、票据到期（若安装 account_cn_bill）、
 * 贷款还款计划（若安装 account_cn_loan），按周/月分桶展示预计流入/流出/净额。
 * 与三大报表/现金流量表完全独立，不复用那套引擎。
 */
export class AccountCnCashForecast extends Component {
    static template = "account_cn_cash_forecast.CashForecast";

    setup() {
        this.orm = useService("orm");

        const today = new Date();
        this.state = useState({
            dateFrom: formatDate(today),
            dateTo: formatDate(addMonths(today, 3)),
            bucket: "month",
            rows: [],
            totals: { inflow: 0, outflow: 0, net: 0 },
            loading: true,
        });

        onWillStart(() => this.loadForecast());
    }

    async loadForecast() {
        this.state.loading = true;
        const data = await this.orm.call(
            "account.cn.cash.forecast",
            "get_forecast_data",
            [false, this.state.dateFrom, this.state.dateTo, this.state.bucket],
        );
        this.state.rows = data.rows;
        this.state.totals = data.totals;
        this.state.loading = false;
    }

    onFilterChanged() {
        this.loadForecast();
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
}

registry.category("actions").add("account_cn_cash_forecast", AccountCnCashForecast);
