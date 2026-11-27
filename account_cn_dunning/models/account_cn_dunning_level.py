# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountCnDunningLevel(models.Model):
    _name = 'account.cn.dunning.level'
    _description = '催收等级'
    _order = 'delay'

    name = fields.Char(string='等级名称', required=True, translate=True)
    delay = fields.Integer(
        string='逾期天数阈值', required=True,
        help='应收账款到期超过这么多天后触发本等级提醒。',
    )
    company_id = fields.Many2one(
        comodel_name='res.company', string='公司', required=True,
        default=lambda self: self.env.company,
    )
    mail_template_id = fields.Many2one(
        comodel_name='mail.template', string='客户邮件模板',
        domain="[('model', '=', 'res.partner')]",
        help='留空则本等级不发送邮件，只做内部提醒。',
    )
    notify_salesperson = fields.Boolean(
        string='同时企微提醒销售员',
        help='客户升级到本等级时，额外提醒其逾期发票上的销售员'
             '（需要安装兼容的第三方企业微信通知模块（本仓库不提供）才会实际发送）。',
    )

    _sql_constraints = [
        ('delay_company_uniq', 'unique(company_id, delay)', '同一公司下逾期天数阈值不能重复。'),
    ]
