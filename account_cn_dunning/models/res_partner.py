# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cn_dunning_exempt = fields.Boolean(string='催款免打扰')
    cn_dunning_level_id = fields.Many2one(
        comodel_name='account.cn.dunning.level', string='当前催收等级',
        compute='_compute_cn_dunning_level',
    )
    cn_dunning_total_overdue = fields.Monetary(
        string='逾期应收总额', compute='_compute_cn_dunning_level',
        currency_field='currency_id',
    )
    cn_dunning_last_level_id = fields.Many2one(
        comodel_name='account.cn.dunning.level', string='上次已提醒等级',
        readonly=True, copy=False,
    )
    cn_dunning_last_sent_date = fields.Datetime(
        string='上次催款时间', readonly=True, copy=False,
    )

    def _cn_get_overdue_receivable_lines(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return self.env['account.move.line'].search([
            ('partner_id', '=', self.id),
            ('company_id', '=', self.env.company.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('reconciled', '=', False),
            ('date_maturity', '<', today),
        ])

    def _compute_cn_dunning_level(self):
        levels = self.env['account.cn.dunning.level'].search([
            ('company_id', '=', self.env.company.id),
        ], order='delay desc')
        today = fields.Date.context_today(self)
        for partner in self:
            lines = False if partner.cn_dunning_exempt else partner._cn_get_overdue_receivable_lines()
            if not lines:
                partner.cn_dunning_level_id = False
                partner.cn_dunning_total_overdue = 0.0
                continue
            max_overdue = max((today - line.date_maturity).days for line in lines)
            partner.cn_dunning_total_overdue = sum(lines.mapped('amount_residual'))
            applicable = levels.filtered(lambda lv: max_overdue >= lv.delay)
            partner.cn_dunning_level_id = applicable[0].id if applicable else False

    def _cn_process_dunning(self):
        self.ensure_one()
        level = self.cn_dunning_level_id
        if not level:
            return
        # 只有升到比上次更高的等级才重新提醒，避免同一等级反复打扰客户
        if self.cn_dunning_last_level_id and self.cn_dunning_last_level_id.delay >= level.delay:
            return

        if level.mail_template_id:
            level.mail_template_id.send_mail(self.id, force_send=False)

        if level.notify_salesperson and 'wechat.notification.service' in self.env:
            salespeople = self._cn_get_overdue_receivable_lines().move_id.invoice_user_id
            if salespeople:
                self.env['wechat.notification.service'].send_notification(
                    user_ids=salespeople.ids,
                    title='客户逾期提醒',
                    content=f'客户"{self.display_name}"的应收账款已进入"{level.name}"催收等级，'
                            f'逾期应收总额约 {self.cn_dunning_total_overdue:.2f}，请及时跟进。',
                    notification_type='warning',
                )

        self.write({
            'cn_dunning_last_level_id': level.id,
            'cn_dunning_last_sent_date': fields.Datetime.now(),
        })

    @api.model
    def _cn_dunning_scan(self):
        """扫描当前公司下所有客户，命中新催收等级的发送提醒。"""
        today = fields.Date.context_today(self)
        overdue_lines = self.env['account.move.line'].search([
            ('company_id', '=', self.env.company.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('reconciled', '=', False),
            ('date_maturity', '<', today),
            ('partner_id', '!=', False),
        ])
        partners = overdue_lines.partner_id.filtered(lambda p: not p.cn_dunning_exempt)
        for partner in partners:
            partner._cn_process_dunning()

    @api.model
    def _cron_cn_dunning_check(self):
        for company in self.env['res.company'].search([]):
            self.with_company(company).sudo()._cn_dunning_scan()

    @api.model
    def action_cn_run_dunning_check(self):
        """手动立即执行催款检查（供菜单入口调用，无需等定时任务）。
        这是一个全公司范围的扫描动作，与在哪条客户记录上调用无关。"""
        self.sudo()._cn_dunning_scan()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '催款检查已完成',
                'message': '已按当前催收等级配置检查并发送本次需要提醒的客户。',
                'type': 'success',
                'sticky': False,
            },
        }
