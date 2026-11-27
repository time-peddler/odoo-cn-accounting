# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models


class AccountCnAssetDepreciationWizard(models.TransientModel):
    _name = 'account.cn.asset.depreciation.wizard'
    _description = '批量计提折旧'

    date = fields.Date(string='计提日期', required=True, default=fields.Date.context_today)
    line_ids = fields.One2many(
        comodel_name='account.cn.asset.depreciation.wizard.line', inverse_name='wizard_id',
        string='本期计提明细',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'line_ids' in fields_list:
            assets = self.env['account.cn.asset'].search([
                ('state', '=', 'running'), ('company_id', '=', self.env.company.id),
            ])
            res['line_ids'] = [Command.create({'asset_id': asset.id}) for asset in assets]
        return res

    def action_confirm(self):
        self.ensure_one()
        moves_by_category = {}
        for line in self.line_ids:
            asset = line.asset_id
            if not asset:
                continue
            amount = asset._cn_compute_next_depreciation_amount(line.workload_amount)
            if not amount:
                continue
            dep_line = self.env['account.cn.asset.depreciation.line'].create({
                'asset_id': asset.id,
                'period_date': self.date,
                'workload_amount': line.workload_amount,
                'depreciation_amount': amount,
            })
            moves_by_category.setdefault(asset.category_id, []).append((asset, dep_line, amount))

        moves = self.env['account.move']
        for category, entries in moves_by_category.items():
            move_lines = []
            total = 0.0
            for asset, dep_line, amount in entries:
                total += amount
                move_lines.append(Command.create({
                    'account_id': category.depreciation_account_id.id,
                    'debit': 0.0,
                    'credit': amount,
                    'name': _('%s 折旧') % asset.name,
                }))
            move_lines.append(Command.create({
                'account_id': category.depreciation_expense_account_id.id,
                'debit': total,
                'credit': 0.0,
                'name': _('%s 本期折旧') % category.name,
            }))
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': category.journal_id.id,
                'company_id': self.env.company.id,
                'date': self.date,
                'ref': _('%(category)s 折旧计提 %(date)s') % {'category': category.name, 'date': self.date},
                'line_ids': move_lines,
            })
            move.action_post()
            for asset, dep_line, amount in entries:
                dep_line.write({'move_id': move.id, 'state': 'posted'})
            moves |= move

        return {
            'type': 'ir.actions.act_window',
            'name': _('折旧凭证'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
        }


class AccountCnAssetDepreciationWizardLine(models.TransientModel):
    _name = 'account.cn.asset.depreciation.wizard.line'
    _description = '批量计提折旧-资产明细'

    wizard_id = fields.Many2one(comodel_name='account.cn.asset.depreciation.wizard')
    asset_id = fields.Many2one(comodel_name='account.cn.asset', string='资产')
    method = fields.Selection(related='asset_id.method', string='折旧方法')
    currency_id = fields.Many2one(related='asset_id.currency_id', string='币种')
    workload_amount = fields.Float(string='本期工作量', help='仅工作量法资产需要填写。')
    preview_amount = fields.Monetary(
        string='预计折旧额', compute='_compute_preview_amount', currency_field='currency_id',
    )

    @api.depends('asset_id', 'workload_amount')
    def _compute_preview_amount(self):
        for line in self:
            line.preview_amount = (
                line.asset_id._cn_compute_next_depreciation_amount(line.workload_amount)
                if line.asset_id else 0.0
            )
