# -*- coding: utf-8 -*-
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class AccountCnCashForecast(models.AbstractModel):
    _name = 'account.cn.cash.forecast'
    _description = '资金计划与现金流预测'

    @api.model
    def _cn_build_buckets(self, date_from, date_to, bucket):
        buckets = []
        cursor = date_from
        if bucket == 'month':
            index = 1
            while cursor <= date_to:
                month_end = cursor.replace(day=1) + relativedelta(months=1, days=-1)
                end = min(month_end, date_to)
                buckets.append({'label': cursor.strftime('%Y-%m'), 'date_from': cursor, 'date_to': end})
                cursor = end + timedelta(days=1)
                index += 1
        else:
            index = 1
            while cursor <= date_to:
                end = min(cursor + timedelta(days=6), date_to)
                buckets.append({
                    'label': _('第%(index)s周（%(start)s ~ %(end)s）') % {
                        'index': index, 'start': cursor, 'end': end,
                    },
                    'date_from': cursor, 'date_to': end,
                })
                cursor = end + timedelta(days=1)
                index += 1
        return buckets

    @api.model
    def _cn_receivable_payable_events(self, company, date_from, date_to):
        domain = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('date_maturity', '>=', date_from),
            ('date_maturity', '<=', date_to),
        ]
        events = []
        for line in self.env['account.move.line'].search(domain):
            if company.currency_id.is_zero(line.amount_residual):
                continue
            # 应收余额通常为正（借方余额）、应付余额通常为负（贷方余额），
            # 直接相加即可得到"预计流入为正、预计流出为负"的统一符号口径
            events.append({'date': line.date_maturity, 'amount': line.amount_residual})
        return events

    @api.model
    def _cn_bill_events(self, company, date_from, date_to):
        if 'account.cn.bill' not in self.env:
            return []
        domain = [
            ('company_id', '=', company.id),
            ('state', '=', 'held'),
            ('maturity_date', '>=', date_from),
            ('maturity_date', '<=', date_to),
        ]
        events = []
        for bill in self.env['account.cn.bill'].search(domain):
            amount = bill.amount if bill.bill_type == 'receivable' else -bill.amount
            events.append({'date': bill.maturity_date, 'amount': amount})
        return events

    @api.model
    def _cn_loan_events(self, company, date_from, date_to):
        if 'account.cn.loan' not in self.env:
            return []
        events = []
        loans = self.env['account.cn.loan'].search([
            ('company_id', '=', company.id), ('state', '=', 'running'),
        ])
        for loan in loans:
            for period in loan._cn_forecast_repayment_schedule(date_from, date_to):
                events.append({'date': period['date'], 'amount': -(period['principal'] + period['interest'])})
        return events

    @api.model
    def get_forecast_data(self, company_id, date_from, date_to, bucket='month'):
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company
        date_from = fields.Date.from_string(date_from)
        date_to = fields.Date.from_string(date_to)
        events = (
            self._cn_receivable_payable_events(company, date_from, date_to)
            + self._cn_bill_events(company, date_from, date_to)
            + self._cn_loan_events(company, date_from, date_to)
        )

        buckets = self._cn_build_buckets(date_from, date_to, bucket)
        rows = []
        totals = {'inflow': 0.0, 'outflow': 0.0, 'net': 0.0}
        for bucket_def in buckets:
            inflow = sum(e['amount'] for e in events if e['amount'] > 0 and bucket_def['date_from'] <= e['date'] <= bucket_def['date_to'])
            outflow = -sum(e['amount'] for e in events if e['amount'] < 0 and bucket_def['date_from'] <= e['date'] <= bucket_def['date_to'])
            rows.append({
                'label': bucket_def['label'],
                'inflow': inflow,
                'outflow': outflow,
                'net': inflow - outflow,
            })
            totals['inflow'] += inflow
            totals['outflow'] += outflow
        totals['net'] = totals['inflow'] - totals['outflow']

        return {'rows': rows, 'totals': totals}
