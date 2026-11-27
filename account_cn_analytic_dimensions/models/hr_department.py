# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='部门辅助核算账户',
        copy=False, readonly=True,
        help='自动生成，供会计分录按部门维度进行辅助核算（分析明细）。',
    )

    @api.model_create_multi
    def create(self, vals_list):
        departments = super().create(vals_list)
        departments._cn_sync_analytic_account()
        return departments

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals or 'company_id' in vals:
            self._cn_sync_analytic_account()
        return res

    def _cn_sync_analytic_account(self):
        plan = self.env.ref(
            'account_cn_analytic_dimensions.analytic_plan_department',
            raise_if_not_found=False,
        )
        if not plan:
            return
        for department in self:
            if department.analytic_account_id:
                if department.analytic_account_id.name != department.name:
                    department.analytic_account_id.name = department.name
                continue
            department.analytic_account_id = self.env['account.analytic.account'].create({
                'name': department.name,
                'plan_id': plan.id,
                'company_id': department.company_id.id,
            })
