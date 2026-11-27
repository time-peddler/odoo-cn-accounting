# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cn_income_tax_rate = fields.Float(
        string='企业所得税税率（%）', default=25.0,
        help='小型微利企业等优惠税率场景，请按实际适用税率自行调整此字段。',
    )
