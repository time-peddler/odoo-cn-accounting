# -*- coding: utf-8 -*-
import base64
import csv
import io

from dateutil import parser as date_parser

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_DEFAULT_COLUMNS = {
    'col_date': '日期',
    'col_label': '摘要',
    'col_income': '收入',
    'col_expense': '支出',
    'col_partner_name': '对方户名',
}


class AccountCnBankImportWizard(models.TransientModel):
    _name = 'account.cn.bank.import.wizard'
    _description = '银行对账单导入'

    journal_id = fields.Many2one(
        comodel_name='account.journal', string='银行日记账', required=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
    )
    attachment = fields.Binary(string='银行流水文件（CSV/Excel）', required=True)
    attachment_filename = fields.Char(string='文件名')
    col_date = fields.Char(string='日期列表头', default=_DEFAULT_COLUMNS['col_date'], required=True)
    col_label = fields.Char(string='摘要列表头', default=_DEFAULT_COLUMNS['col_label'], required=True)
    col_income = fields.Char(string='收入列表头', default=_DEFAULT_COLUMNS['col_income'], required=True)
    col_expense = fields.Char(string='支出列表头', default=_DEFAULT_COLUMNS['col_expense'], required=True)
    col_partner_name = fields.Char(string='对方户名列表头', default=_DEFAULT_COLUMNS['col_partner_name'])
    line_ids = fields.One2many(
        comodel_name='account.cn.bank.import.wizard.line', inverse_name='wizard_id', string='预览行',
    )

    def _cn_read_rows(self):
        self.ensure_one()
        raw = base64.b64decode(self.attachment)
        filename = (self.attachment_filename or '').lower()
        if filename.endswith('.csv'):
            text = raw.decode('utf-8-sig')
            return list(csv.DictReader(io.StringIO(text)))
        if filename.endswith('.xlsx'):
            try:
                from openpyxl import load_workbook
            except ImportError:
                raise UserError(_('当前环境未安装 Excel 解析库，请改为上传 CSV 格式的文件。'))
            workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            sheet = workbook.worksheets[0]
            rows_iter = sheet.iter_rows(values_only=True)
            header = [str(h).strip() if h is not None else '' for h in next(rows_iter)]
            rows = []
            for row in rows_iter:
                rows.append({header[i]: row[i] for i in range(len(header)) if i < len(row)})
            return rows
        raise UserError(_('只支持 CSV 或 Excel（.xlsx）格式的文件。'))

    @staticmethod
    def _cn_to_date(value):
        if hasattr(value, 'year'):
            return value.date() if hasattr(value, 'date') and callable(value.date) else value
        try:
            return date_parser.parse(str(value), dayfirst=False, yearfirst=True).date()
        except (ValueError, OverflowError):
            return False

    @staticmethod
    def _cn_to_float(value):
        if value in (None, ''):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).replace(',', '').strip())
        except ValueError:
            return 0.0

    def action_preview(self):
        self.ensure_one()
        rows = self._cn_read_rows()
        line_vals = []
        for row in rows:
            date_value = row.get(self.col_date)
            if not date_value:
                continue
            parsed_date = self._cn_to_date(date_value)
            if not parsed_date:
                continue
            income = self._cn_to_float(row.get(self.col_income))
            expense = self._cn_to_float(row.get(self.col_expense))
            line_vals.append(Command.create({
                'date': parsed_date,
                'label': str(row.get(self.col_label) or ''),
                'amount': income - expense,
                'partner_name': str(row.get(self.col_partner_name) or '') if self.col_partner_name else '',
                'selected': True,
            }))
        if not line_vals:
            raise UserError(_('未解析到任何有效行，请检查文件内容和列表头映射是否正确。'))
        self.line_ids = [Command.clear()] + line_vals
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _cn_is_duplicate(self, journal, line):
        existing_moves = self.env['account.move'].search([
            ('journal_id', '=', journal.id),
            ('date', '=', line.date),
            ('ref', '=', line.label),
        ])
        for move in existing_moves:
            if any(
                move.currency_id.is_zero(abs(l.debit - l.credit) - abs(line.amount))
                for l in move.line_ids
            ):
                return True
        return False

    def action_import(self):
        self.ensure_one()
        company = self.journal_id.company_id or self.env.company
        suspense_account = company.cn_bank_import_suspense_account_id
        if not suspense_account:
            raise UserError(_('请先在公司设置里配置"银行导入暂存科目"。'))
        if not self.journal_id.default_account_id:
            raise UserError(_('所选银行日记账未配置默认科目。'))

        created = 0
        skipped = 0
        for line in self.line_ids.filtered('selected'):
            if line.amount == 0:
                continue
            if self._cn_is_duplicate(self.journal_id, line):
                skipped += 1
                continue
            amount = abs(line.amount)
            bank_debit, bank_credit = (amount, 0.0) if line.amount > 0 else (0.0, amount)
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': self.journal_id.id,
                'company_id': company.id,
                'date': line.date,
                'ref': line.label,
                'line_ids': [
                    Command.create({
                        'account_id': self.journal_id.default_account_id.id,
                        'debit': bank_debit, 'credit': bank_credit,
                        'name': line.label, 'partner_id': line.partner_id.id if line.partner_id else False,
                    }),
                    Command.create({
                        'account_id': suspense_account.id,
                        'debit': bank_credit, 'credit': bank_debit,
                        'name': line.label, 'partner_id': line.partner_id.id if line.partner_id else False,
                    }),
                ],
            })
            move.action_post()
            created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('导入完成'),
                'message': _('新建 %(created)s 条日记账分录，跳过 %(skipped)s 条重复行。') % {
                    'created': created, 'skipped': skipped,
                },
                'sticky': True,
            },
        }


class AccountCnBankImportWizardLine(models.TransientModel):
    _name = 'account.cn.bank.import.wizard.line'
    _description = '银行对账单导入-预览行'

    wizard_id = fields.Many2one(comodel_name='account.cn.bank.import.wizard')
    selected = fields.Boolean(string='导入', default=True)
    date = fields.Date(string='日期', required=True)
    label = fields.Char(string='摘要')
    amount = fields.Monetary(string='净发生额（收入为正）', currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.journal_id.currency_id', string='币种')
    partner_name = fields.Char(string='对方户名')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='匹配的往来单位', compute='_compute_partner_id', store=True, readonly=False,
    )

    @api.depends('partner_name')
    def _compute_partner_id(self):
        for line in self:
            partner = False
            if line.partner_name:
                partner = self.env['res.partner'].search([('name', '=', line.partner_name)], limit=1)
            line.partner_id = partner
