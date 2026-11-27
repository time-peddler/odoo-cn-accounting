# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cn_urban_maintenance_tax_rate = fields.Float(
        string='城建税率（%）', default=7.0,
        help='按注册地不同：市区 7% / 县城镇 5% / 其他 3%，请按实际情况调整。',
    )
    cn_education_surcharge_rate = fields.Float(
        string='教育费附加率（%）', default=3.0,
    )
    cn_local_education_surcharge_rate = fields.Float(
        string='地方教育费附加率（%）', default=2.0,
    )
