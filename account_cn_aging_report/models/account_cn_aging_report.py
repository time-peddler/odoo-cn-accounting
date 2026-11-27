# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models


class AccountCnAgingReport(models.AbstractModel):
    _name = 'account.cn.aging.report'
    _description = '往来账龄分析表'

    _BUCKET_LABELS = ['未到期', '1-30 天', '31-60 天', '61-90 天', '90 天以上']
    # 每个账龄区间对应的逾期天数范围（含两端），None 表示不设上/下限
    _BUCKET_DAY_RANGES = [
        (None, 0),
        (1, 30),
        (31, 60),
        (61, 90),
        (91, None),
    ]

    @api.model
    def _cn_bucket_index(self, overdue_days):
        for idx, (low, high) in enumerate(self._BUCKET_DAY_RANGES):
            if (low is None or overdue_days >= low) and (high is None or overdue_days <= high):
                return idx
        return len(self._BUCKET_DAY_RANGES) - 1

    @api.model
    def _cn_bucket_date_domain(self, as_of, bucket_index):
        """把"逾期天数区间"翻译成对 date_maturity 的过滤条件。
        overdue_days = (as_of - date_maturity).days，所以天数下限对应到期日上限，反之亦然。"""
        low, high = self._BUCKET_DAY_RANGES[bucket_index]
        domain = []
        if low is not None:
            domain.append(('date_maturity', '<=', as_of - timedelta(days=low)))
        if high is not None:
            domain.append(('date_maturity', '>=', as_of - timedelta(days=high)))
        return domain

    @api.model
    def _cn_base_domain(self, account_type):
        return [
            ('company_id', '=', self.env.company.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', account_type),
            ('reconciled', '=', False),
            ('date_maturity', '!=', False),
        ]

    @api.model
    def get_report_data(self, account_type, as_of_date):
        """account_type 传 'asset_receivable'（客户账龄）或 'liability_payable'
        （供应商账龄）。返回结构：
            {
                'bucket_labels': [...],
                'rows': [{'partner_id', 'partner_name', 'buckets': [...], 'total',
                          'drilldown_domains': [...]}, ...],
                'totals': [...], 'grand_total': float,
            }
        """
        company = self.env.company
        # liability_payable 科目正常是贷方余额，amount_residual 的口径与
        # res.partner._credit_debit_get 一致，需要取反才能得到"应付总额"为正数
        sign = -1 if account_type == 'liability_payable' else 1
        as_of = fields.Date.from_string(as_of_date)

        lines = self.env['account.move.line'].search(self._cn_base_domain(account_type))

        partner_rows = {}
        for line in lines:
            amount = sign * line.amount_residual
            if company.currency_id.is_zero(amount):
                continue
            overdue_days = (as_of - line.date_maturity).days
            idx = self._cn_bucket_index(overdue_days)
            partner = line.partner_id
            row = partner_rows.setdefault(partner.id, {
                'partner_id': partner.id,
                'partner_name': partner.display_name or _('（无往来单位）'),
                'buckets': [0.0] * len(self._BUCKET_LABELS),
            })
            row['buckets'][idx] += amount

        base_domain = self._cn_base_domain(account_type)
        rows = []
        totals = [0.0] * len(self._BUCKET_LABELS)
        for row in partner_rows.values():
            row_total = sum(row['buckets'])
            if company.currency_id.is_zero(row_total):
                continue
            row['total'] = row_total
            row['drilldown_domains'] = [
                base_domain + [('partner_id', '=', row['partner_id'])]
                + self._cn_bucket_date_domain(as_of, idx)
                for idx in range(len(self._BUCKET_LABELS))
            ]
            rows.append(row)
            for i, v in enumerate(row['buckets']):
                totals[i] += v
        rows.sort(key=lambda r: r['partner_name'])

        return {
            'bucket_labels': self._BUCKET_LABELS,
            'rows': rows,
            'totals': totals,
            'grand_total': sum(totals),
        }
