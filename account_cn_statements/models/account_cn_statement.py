# -*- coding: utf-8 -*-
import ast

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# 报表公式中允许出现的算术运算符，其余一律拒绝，避免任意代码执行
_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)


class AccountCnStatement(models.Model):
    _name = 'account.cn.statement'
    _description = '中国会计准则财务报表'
    _order = 'id'

    name = fields.Char(string='报表名称', required=True, translate=True)
    code = fields.Selection(
        selection=[
            ('balance_sheet', '资产负债表'),
            ('income_statement', '利润表'),
            ('cash_flow', '现金流量表'),
        ],
        string='报表类型',
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name='account.cn.statement.line',
        inverse_name='statement_id',
        string='报表行',
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', '同一类型的报表只能定义一份。'),
    ]

    def get_report_data(self, date_from, date_to, comparison=False,
                         cmp_date_from=None, cmp_date_to=None, company_id=None):
        """计算并返回报表的展示数据（供前端 OWL 组件调用）。

        返回结构：
            {
                'statement_name': str,
                'date_from': str, 'date_to': str,
                'comparison': bool, 'cmp_date_from': str, 'cmp_date_to': str,
                'lines': [
                    {
                        'id', 'code', 'name', 'level', 'line_type',
                        'is_subtotal', 'note',
                        'current': float | None,
                        'comparison': float | None,
                        'drilldown_domain': list | False,
                    }, ...
                ],
            }
        """
        self.ensure_one()
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company

        root_lines = self.line_ids.filtered(lambda l: not l.parent_id)
        flattened = root_lines._flatten_tree()

        current_values = self.line_ids._compute_period_values(company, date_from, date_to)
        cmp_values = {}
        if comparison and cmp_date_from and cmp_date_to:
            cmp_values = self.line_ids._compute_period_values(company, cmp_date_from, cmp_date_to)

        lines_data = []
        for line, level in flattened:
            drilldown_domain = False
            if line.line_type in ('detail', 'cash_flow'):
                drilldown_domain = line._build_amount_domain(company, date_from, date_to)
            lines_data.append({
                'id': line.id,
                'code': line.code,
                'name': line.name,
                'level': level,
                'line_type': line.line_type,
                'is_subtotal': line.is_subtotal,
                'note': line.note or False,
                'current': current_values.get(line.code),
                'comparison': cmp_values.get(line.code) if comparison else None,
                'drilldown_domain': drilldown_domain,
            })

        return {
            'statement_name': self.name,
            'date_from': date_from,
            'date_to': date_to,
            'comparison': bool(comparison),
            'cmp_date_from': cmp_date_from,
            'cmp_date_to': cmp_date_to,
            'lines': lines_data,
        }


class AccountCnStatementLine(models.Model):
    _name = 'account.cn.statement.line'
    _description = '中国会计准则财务报表行'
    _order = 'sequence, id'

    statement_id = fields.Many2one(
        comodel_name='account.cn.statement', string='所属报表',
        required=True, ondelete='cascade',
    )
    parent_id = fields.Many2one(
        comodel_name='account.cn.statement.line', string='上级行',
        ondelete='cascade',
    )
    child_ids = fields.One2many(
        comodel_name='account.cn.statement.line', inverse_name='parent_id',
        string='下级行',
    )
    sequence = fields.Integer(string='顺序', default=10)
    code = fields.Char(string='行编码', required=True,
                        help='报表内部唯一标识，供公式互相引用，不对用户展示。')
    name = fields.Char(string='行名称', required=True, translate=True)
    line_type = fields.Selection(
        selection=[
            ('section', '分组标题'),
            ('detail', '按科目编码取数'),
            ('cash_flow', '按现金流量项目取数'),
            ('formula', '公式/子行汇总'),
        ],
        string='取数方式',
        required=True,
        default='section',
    )
    account_code_prefixes = fields.Char(
        string='科目编码',
        help='逗号分隔的科目编码前缀或区间，例如 "1001,1002" 或 "1401-1406"。'
             '"取数方式"为"按科目编码取数"时使用。',
    )
    balance_side = fields.Selection(
        selection=[('debit', '借方为正'), ('credit', '贷方为正')],
        string='余额方向',
        help='资产、成本、费用类科目通常"借方为正"；'
             '负债、所有者权益、收入类科目通常"贷方为正"。',
    )
    cash_flow_item_id = fields.Many2one(
        comodel_name='account.cn.cash.flow.item', string='现金流量项目',
        help='"取数方式"为"按现金流量项目取数"时使用。',
    )
    formula = fields.Char(
        string='汇总公式',
        help='可引用同一报表内其它行的"行编码"做四则运算，例如 '
             '"CURRENT_ASSETS + NONCURRENT_ASSETS"；留空则默认为下级行求和。',
    )
    is_subtotal = fields.Boolean(string='加粗显示（合计/总计行）')
    note = fields.Char(string='备注', translate=True)

    _sql_constraints = [
        ('statement_code_uniq', 'unique(statement_id, code)',
         '同一报表内的行编码不能重复。'),
    ]

    def _flatten_tree(self, level=0):
        """按 sequence 深度优先展开为 [(line, level), ...] 列表，保持展示顺序。"""
        result = []
        for line in self.sorted(key=lambda l: (l.sequence, l.id)):
            result.append((line, level))
            result.extend(line.child_ids._flatten_tree(level=level + 1))
        return result

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

    def _build_amount_domain(self, company, date_from, date_to):
        """构造用于取数 / 明细钻取的 account.move.line 过滤域。"""
        self.ensure_one()
        domain = [
            ('parent_state', '=', 'posted'),
            ('company_id', '=', company.id),
        ]
        if self.line_type == 'detail':
            tokens = self._parse_code_prefixes(self.account_code_prefixes)
            if not tokens:
                return False
            prefix_domain = []
            for _i in range(len(tokens) - 1):
                prefix_domain.append('|')
            for token in tokens:
                prefix_domain.append(('account_id.code', '=like', f'{token}%'))
            domain += prefix_domain
            if self.statement_id.code == 'income_statement':
                domain.append(('date', '>=', date_from))
            domain.append(('date', '<=', date_to))
        elif self.line_type == 'cash_flow':
            if not self.cash_flow_item_id:
                return False
            domain += [
                ('cn_cash_flow_item_id', '=', self.cash_flow_item_id.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ]
        else:
            return False
        return domain

    def _compute_raw_value(self, company, date_from, date_to):
        """对单行做一次聚合查询，返回按余额方向处理符号后的金额。"""
        self.ensure_one()
        domain = self._build_amount_domain(company, date_from, date_to)
        if not domain:
            return 0.0
        rows = self.env['account.move.line']._read_group(
            domain, aggregates=['debit:sum', 'credit:sum'],
        )
        debit_sum, credit_sum = rows[0] if rows else (0.0, 0.0)
        if self.line_type == 'cash_flow':
            # 汇率变动影响本身有正有负，保留符号；其余现金流量项目按惯例以正数列示流入/流出金额
            if self.cash_flow_item_id.category == 'fx':
                return debit_sum - credit_sum
            return abs(debit_sum - credit_sum)
        if self.balance_side == 'credit':
            return credit_sum - debit_sum
        return debit_sum - credit_sum

    @api.model
    def _eval_formula(self, formula, code_to_value):
        """仅允许 +-*/() 与行编码引用的安全表达式求值，杜绝任意代码执行。"""
        try:
            tree = ast.parse(formula, mode='eval')
        except SyntaxError:
            raise UserError(_('报表公式格式有误：%s') % formula)

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
                left, right = _eval(node.left), _eval(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                return left / right if right else 0.0
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARYOPS):
                value = _eval(node.operand)
                return -value if isinstance(node.op, ast.USub) else value
            if isinstance(node, ast.Name):
                if node.id not in code_to_value:
                    raise UserError(_('报表公式引用了未知的行编码：%s') % node.id)
                return code_to_value[node.id] or 0.0
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            raise UserError(_('报表公式包含不支持的表达式：%s') % formula)

        return _eval(tree)

    def _iter_value_children(self, line):
        """展开 line 的下级行：遇到"分组标题"行（无金额）时穿透取其下级，
        直到取到真正携带金额的行（detail/cash_flow/formula）为止。"""
        for child in line.child_ids:
            if child.line_type == 'section':
                yield from self._iter_value_children(child)
            else:
                yield child

    def _compute_period_values(self, company, date_from, date_to):
        """计算 self（某报表全部行）在给定期间内，每个行编码对应的金额。"""
        values = {}
        lines_by_code = {line.code: line for line in self}

        for line in self:
            if line.line_type in ('detail', 'cash_flow'):
                values[line.code] = line._compute_raw_value(company, date_from, date_to)

        resolving = set()

        def resolve(line):
            if line.code in values:
                return values[line.code]
            if line.line_type == 'section':
                return None
            if line.code in resolving:
                raise UserError(_('报表行公式存在循环引用：%s') % line.code)
            resolving.add(line.code)
            if line.formula:
                # 公式可能引用尚未解析的行，先递归解析它引用到的行
                for name_node in ast.walk(ast.parse(line.formula, mode='eval')):
                    if isinstance(name_node, ast.Name) and name_node.id in lines_by_code:
                        resolve(lines_by_code[name_node.id])
                snapshot = {code: (val or 0.0) for code, val in values.items()}
                value = self._eval_formula(line.formula, snapshot)
            else:
                value = sum(
                    (resolve(child) or 0.0)
                    for child in self._iter_value_children(line)
                )
            values[line.code] = value
            resolving.discard(line.code)
            return value

        for line in self:
            if line.line_type == 'formula':
                resolve(line)

        return values
