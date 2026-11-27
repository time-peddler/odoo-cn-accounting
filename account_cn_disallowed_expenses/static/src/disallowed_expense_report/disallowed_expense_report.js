/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

function formatDate(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function firstDayOfYear(date) {
    return new Date(date.getFullYear(), 0, 1);
}

/**
 * 纳税调整/不可抵扣费用报表：按类别展示实际发生额/可扣除限额/纳税调整
 * 增加额，点击金额钻取到该类别名下科目在期间内的分录明细。
 */
export class AccountCnDisallowedExpenseReport extends Component {
    static template = "account_cn_disallowed_expenses.DisallowedExpenseReport";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        const today = new Date();
        this.state = useState({
            dateFrom: formatDate(firstDayOfYear(today)),
            dateTo: formatDate(today),
            rows: [],
            totals: { actual_amount: 0, deductible_amount: 0, adjustment_amount: 0 },
            loading: true,
        });

        onWillStart(() => this.loadReport());
    }

    async loadReport() {
        this.state.loading = true;
        // 不传公司，由后端取当前会话的活动公司（与 account_cn_aging_report/
        // account_cn_statements 的前端调用方式一致）
        const data = await this.orm.call(
            "account.cn.disallowed.expense.report",
            "get_report_data",
            [false, this.state.dateFrom, this.state.dateTo],
        );
        this.state.rows = data.rows;
        this.state.totals = data.totals;
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

    onCellClick(row) {
        if (!row.actual_amount) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.category_name,
            res_model: "account.move.line",
            view_mode: "list,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: row.drilldown_domain,
            target: "current",
        });
    }
}

registry.category("actions").add("account_cn_disallowed_expense_report", AccountCnDisallowedExpenseReport);
