/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

function formatDate(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function defaultPeriod() {
    const today = new Date();
    const dateFrom = new Date(today.getFullYear(), 0, 1);
    return { dateFrom: formatDate(dateFrom), dateTo: formatDate(today) };
}

function shiftYear(dateStr, offset) {
    const [y, m, d] = dateStr.split("-").map(Number);
    return formatDate(new Date(y + offset, m - 1, d));
}

/**
 * 中国会计准则动态财务报表（资产负债表/利润表/现金流量表）的通用展示组件。
 * 通过 params.statement_code 区分具体展示哪一张报表，三张报表共用同一套
 * 取数、渲染、钻取逻辑。
 */
export class AccountCnStatementReport extends Component {
    static template = "account_cn_statements.StatementReport";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.statementCode = this.props.action?.params?.statement_code;
        const { dateFrom, dateTo } = defaultPeriod();

        this.state = useState({
            statementName: "",
            statementId: false,
            dateFrom,
            dateTo,
            comparison: false,
            lines: [],
            loading: true,
        });

        onWillStart(() => this.loadReport());
    }

    async loadReport() {
        this.state.loading = true;
        if (!this.state.statementId) {
            const statements = await this.orm.searchRead(
                "account.cn.statement",
                [["code", "=", this.statementCode]],
                ["id", "name"],
            );
            if (!statements.length) {
                this.state.loading = false;
                return;
            }
            this.state.statementId = statements[0].id;
            this.state.statementName = statements[0].name;
        }

        const cmpDateFrom = shiftYear(this.state.dateFrom, -1);
        const cmpDateTo = shiftYear(this.state.dateTo, -1);

        const data = await this.orm.call(
            "account.cn.statement",
            "get_report_data",
            [
                [this.state.statementId],
                this.state.dateFrom,
                this.state.dateTo,
                this.state.comparison,
                cmpDateFrom,
                cmpDateTo,
            ],
        );
        this.state.lines = data.lines;
        this.state.loading = false;
    }

    onDateChanged() {
        this.loadReport();
    }

    onToggleComparison() {
        this.state.comparison = !this.state.comparison;
        this.loadReport();
    }

    formatAmount(value) {
        if (value === null || value === undefined) {
            return "";
        }
        return new Intl.NumberFormat("zh-CN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }

    isClickable(line) {
        return Boolean(line.drilldown_domain);
    }

    onLineClick(line) {
        if (!this.isClickable(line)) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: line.name,
            res_model: "account.move.line",
            view_mode: "list,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: line.drilldown_domain,
            target: "current",
        });
    }
}

registry.category("actions").add("account_cn_statement_report", AccountCnStatementReport);
