# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# 进项税额转出等手工调整分录的科目编码前缀（l10n_cn 科目表已预置，
# 但没有任何税率自动分流到这个二级科目，只能靠手工记账+按编码取数）
_INPUT_VAT_TRANSFERRED_OUT_PREFIX = '2221.01.04'


class AccountCnVatReturn(models.Model):
    _name = 'account.cn.vat.return'
    _description = '增值税及附加税费申报表'
    _order = 'date_to desc'

    name = fields.Char(string='名称', compute='_compute_name', store=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', string='币种')
    date_from = fields.Date(string='起始日期', required=True)
    date_to = fields.Date(string='截止日期', required=True)
    state = fields.Selection(
        selection=[('draft', '编制中'), ('confirmed', '已确认')],
        string='状态', default='draft', required=True, readonly=True, copy=False,
    )

    opening_credit = fields.Monetary(string='期初留抵税额', currency_field='currency_id')
    output_vat_amount = fields.Monetary(string='销项税额', currency_field='currency_id')
    input_vat_amount = fields.Monetary(string='进项税额', currency_field='currency_id')
    input_vat_transferred_out = fields.Monetary(string='进项税额转出', currency_field='currency_id')

    deductible_vat_total = fields.Monetary(
        string='应抵扣税额合计', compute='_compute_vat_amounts', store=True, currency_field='currency_id',
    )
    payable_vat_amount = fields.Monetary(
        string='应纳税额', compute='_compute_vat_amounts', store=True, currency_field='currency_id',
    )
    closing_credit = fields.Monetary(
        string='期末留抵税额', compute='_compute_vat_amounts', store=True, currency_field='currency_id',
    )

    urban_maintenance_tax = fields.Monetary(
        string='城建税', compute='_compute_surcharges', store=True, currency_field='currency_id',
    )
    education_surcharge = fields.Monetary(
        string='教育费附加', compute='_compute_surcharges', store=True, currency_field='currency_id',
    )
    local_education_surcharge = fields.Monetary(
        string='地方教育费附加', compute='_compute_surcharges', store=True, currency_field='currency_id',
    )
    surcharge_total = fields.Monetary(
        string='附加税费合计', compute='_compute_surcharges', store=True, currency_field='currency_id',
    )

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for record in self:
            if record.date_from and record.date_to:
                record.name = _('%(date_from)s 至 %(date_to)s 增值税申报') % {
                    'date_from': record.date_from,
                    'date_to': record.date_to,
                }
            else:
                record.name = _('增值税申报')

    @api.constrains('date_from', 'date_to', 'company_id')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(_('"%s"：起始日期不能晚于截止日期。') % record.name)
            overlapping = self.search_count([
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id),
                ('date_from', '<=', record.date_to),
                ('date_to', '>=', record.date_from),
            ])
            if overlapping:
                raise ValidationError(_('该公司在此期间内已存在增值税申报记录，请勿重复编制。'))

    @api.depends('output_vat_amount', 'input_vat_amount', 'input_vat_transferred_out', 'opening_credit')
    def _compute_vat_amounts(self):
        for record in self:
            deductible_total = (
                record.input_vat_amount - record.input_vat_transferred_out + record.opening_credit
            )
            record.deductible_vat_total = deductible_total
            record.payable_vat_amount = max(0.0, record.output_vat_amount - deductible_total)
            record.closing_credit = max(0.0, deductible_total - record.output_vat_amount)

    @api.depends('payable_vat_amount', 'company_id.cn_urban_maintenance_tax_rate',
                 'company_id.cn_education_surcharge_rate', 'company_id.cn_local_education_surcharge_rate')
    def _compute_surcharges(self):
        for record in self:
            company = record.company_id
            record.urban_maintenance_tax = record.payable_vat_amount * (company.cn_urban_maintenance_tax_rate or 0.0) / 100.0
            record.education_surcharge = record.payable_vat_amount * (company.cn_education_surcharge_rate or 0.0) / 100.0
            record.local_education_surcharge = record.payable_vat_amount * (company.cn_local_education_surcharge_rate or 0.0) / 100.0
            record.surcharge_total = (
                record.urban_maintenance_tax + record.education_surcharge + record.local_education_surcharge
            )

    @staticmethod
    def _parse_code_prefixes(prefixes):
        """将 "1001,1401-1406" 这样的配置展开为一组具体的科目编码前缀。"""
        tokens = []
        for part in (prefixes or '').split(','):
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                start, end = part.split('-', 1)
                start, end = start.strip(), end.strip()
                width = len(start)
                for n in range(int(start), int(end) + 1):
                    tokens.append(str(n).zfill(width))
            else:
                tokens.append(part)
        return tokens

    def _cn_find_prior_return(self):
        self.ensure_one()
        return self.search([
            ('id', '!=', self.id),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'confirmed'),
            ('date_to', '<', self.date_from),
        ], order='date_to desc', limit=1)

    def _cn_compute_output_input_vat(self):
        self.ensure_one()
        base_domain = [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        rows = self.env['account.move.line']._read_group(
            base_domain + [('tax_line_id.type_tax_use', '=', 'sale')],
            aggregates=['debit:sum', 'credit:sum'],
        )
        debit_sum, credit_sum = rows[0] if rows else (0.0, 0.0)
        output_vat = credit_sum - debit_sum

        rows = self.env['account.move.line']._read_group(
            base_domain + [('tax_line_id.type_tax_use', '=', 'purchase')],
            aggregates=['debit:sum', 'credit:sum'],
        )
        debit_sum, credit_sum = rows[0] if rows else (0.0, 0.0)
        input_vat = debit_sum - credit_sum

        tokens = self._parse_code_prefixes(_INPUT_VAT_TRANSFERRED_OUT_PREFIX)
        prefix_domain = []
        for _i in range(len(tokens) - 1):
            prefix_domain.append('|')
        for token in tokens:
            prefix_domain.append(('account_id.code', '=like', f'{token}%'))
        rows = self.env['account.move.line']._read_group(
            base_domain + prefix_domain, aggregates=['debit:sum', 'credit:sum'],
        )
        debit_sum, credit_sum = rows[0] if rows else (0.0, 0.0)
        transferred_out = credit_sum - debit_sum

        return output_vat, input_vat, transferred_out

    def action_generate(self):
        for record in self.filtered(lambda r: r.state == 'draft'):
            output_vat, input_vat, transferred_out = record._cn_compute_output_input_vat()
            prior_return = record._cn_find_prior_return()
            vals = {
                'output_vat_amount': output_vat,
                'input_vat_amount': input_vat,
                'input_vat_transferred_out': transferred_out,
            }
            if prior_return:
                vals['opening_credit'] = prior_return.closing_credit
            record.write(vals)

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('只有编制中的申报记录才能确认。'))
            record.state = 'confirmed'

    def action_reset_to_draft(self):
        self.filtered(lambda r: r.state == 'confirmed').write({'state': 'draft'})
