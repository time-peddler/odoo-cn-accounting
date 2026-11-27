# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='员工辅助核算账户',
        copy=False, readonly=True,
        help='自动生成，供会计分录按员工维度进行辅助核算（分析明细）。',
    )

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._cn_sync_analytic_account()
        return employees

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals or 'company_id' in vals:
            self._cn_sync_analytic_account()
        return res

    def _cn_sync_analytic_account(self):
        plan = self.env.ref(
            'account_cn_analytic_dimensions.analytic_plan_employee',
            raise_if_not_found=False,
        )
        if not plan:
            return
        for employee in self:
            if employee.analytic_account_id:
                if employee.analytic_account_id.name != employee.name:
                    employee.analytic_account_id.name = employee.name
                continue
            employee.analytic_account_id = self.env['account.analytic.account'].create({
                'name': employee.name,
                'plan_id': plan.id,
                'company_id': employee.company_id.id,
            })
