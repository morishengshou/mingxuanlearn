有的。Odoo 18 里如果一个模型有 **800+ 字段**，通常不建议在业务逻辑里大量写这种代码：

```python
vals = {
    'field_a': data.get('field_a'),
    'field_b': data.get('field_b'),
    'field_c': data.get('field_c'),
    # ...
}
```

可以用 **动态字段映射**、**配置化映射**、**反射式字段过滤** 来优化。

下面给你几种常用方案。

---

## 方案一：基于 `_fields` 自动过滤字段

如果外部数据的 key 和 Odoo 字段名一致，这是最简单、最推荐的方式。

```python
def _prepare_vals_from_data(self, data):
    model_fields = self._fields

    vals = {
        key: value
        for key, value in data.items()
        if key in model_fields
    }

    return vals
```

使用：

```python
data = {
    'name': '测试',
    'phone': '13800000000',
    'unknown_field': 'xxx',
}

vals = self._prepare_vals_from_data(data)
record = self.env['your.model'].create(vals)
```

这样 `unknown_field` 会被自动过滤掉，避免 `Invalid field` 报错。

---

## 方案二：只允许写入普通字段，排除计算字段、只读字段

800 多个字段时，很多可能是：

- `compute` 字段
- `related` 字段
- `readonly` 字段
- `one2many`
- 系统字段

这些字段不一定适合写入。

可以做一个更安全的动态映射：

```python
def _get_writable_fields(self):
    writable_fields = {}

    for name, field in self._fields.items():
        if name in ('id', 'create_uid', 'create_date', 'write_uid', 'write_date', '__last_update'):
            continue

        if field.compute and not field.inverse:
            continue

        if field.readonly:
            continue

        writable_fields[name] = field

    return writable_fields


def _prepare_vals_from_data(self, data):
    writable_fields = self._get_writable_fields()

    vals = {
        key: value
        for key, value in data.items()
        if key in writable_fields
    }

    return vals
```

---

## 方案三：外部字段名和 Odoo 字段名不一致时，用映射表

比如外部系统给你：

```python
{
    '客户名称': '张三',
    '手机号': '13800000000',
    '邮箱': 'test@example.com'
}
```

而 Odoo 字段是：

```python
name
phone
email
```

可以定义映射字典：

```python
FIELD_MAPPING = {
    '客户名称': 'name',
    '手机号': 'phone',
    '邮箱': 'email',
}
```

然后转换：

```python
def _prepare_vals_from_mapping(self, data):
    vals = {}

    for external_key, value in data.items():
        odoo_field = FIELD_MAPPING.get(external_key)

        if not odoo_field:
            continue

        if odoo_field not in self._fields:
            continue

        vals[odoo_field] = value

    return vals
```

使用：

```python
vals = self._prepare_vals_from_mapping(data)
self.env['your.model'].create(vals)
```

---

## 方案四：把字段映射做成可配置模型

如果 800 多个字段经常变化，不建议写死在代码里。可以建一个映射配置模型。

### 1. 定义映射模型

```python
from odoo import models, fields


class FieldMapping(models.Model):
    _name = 'field.mapping'
    _description = 'Field Mapping'

    name = fields.Char(string='映射名称')
    model_name = fields.Char(string='模型')
    external_field = fields.Char(string='外部字段')
    odoo_field = fields.Char(string='Odoo字段')
    active = fields.Boolean(default=True)
```

### 2. 使用配置进行动态转换

```python
def _get_field_mapping(self):
    mappings = self.env['field.mapping'].search([
        ('model_name', '=', self._name),
        ('active', '=', True),
    ])

    return {
        m.external_field: m.odoo_field
        for m in mappings
    }


def _prepare_vals_from_config_mapping(self, data):
    mapping = self._get_field_mapping()
    vals = {}

    for external_key, value in data.items():
        odoo_field = mapping.get(external_key)

        if not odoo_field:
            continue

        if odoo_field not in self._fields:
            continue

        vals[odoo_field] = value

    return vals
```

这种方式适合：

- Excel 导入
- API 对接
- 中台数据同步
- 第三方系统字段不稳定
- 不同客户字段映射规则不同

---

## 方案五：使用 `ir.model.fields` 动态获取字段

如果你不想直接依赖 `_fields`，也可以从 Odoo 元数据中获取字段。

```python
def _get_model_field_names(self):
    fields_records = self.env['ir.model.fields'].search([
        ('model', '=', self._name),
    ])

    return set(fields_records.mapped('name'))


def _prepare_vals(self, data):
    field_names = self._get_model_field_names()

    return {
        key: value
        for key, value in data.items()
        if key in field_names
    }
```

不过在代码内部，通常直接用：

```python
self._fields
```

性能会更好。

---

## 方案六：字段分组映射

如果字段很多，建议按业务分组，比如：

```python
BASE_FIELDS = {
    'name',
    'company_id',
    'user_id',
}

CONTACT_FIELDS = {
    'phone',
    'mobile',
    'email',
}

FINANCE_FIELDS = {
    'credit_limit',
    'payment_term_id',
}

ALL_ALLOWED_FIELDS = BASE_FIELDS | CONTACT_FIELDS | FINANCE_FIELDS
```

然后：

```python
def _prepare_vals_by_group(self, data, groups=None):
    allowed_fields = set()

    if not groups:
        allowed_fields = ALL_ALLOWED_FIELDS
    else:
        for group in groups:
            allowed_fields |= group

    return {
        key: value
        for key, value in data.items()
        if key in allowed_fields and key in self._fields
    }
```

适合场景：

- 创建时只允许部分字段
- 更新时只允许部分字段
- 不同接口允许写入不同字段

---

## 方案七：Many2one / Selection / Date 字段动态转换

如果字段类型很多，不能只是简单赋值。可以根据字段类型动态处理。

```python
from odoo import fields as odoo_fields


def _convert_value_by_field_type(self, field, value):
    if value in (None, ''):
        return False

    if field.type == 'many2one':
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            record = self.env[field.comodel_name].search([('name', '=', value)], limit=1)
            return record.id if record else False

    if field.type == 'integer':
        return int(value)

    if field.type == 'float':
        return float(value)

    if field.type == 'boolean':
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', '是')
        return bool(value)

    if field.type == 'date':
        return odoo_fields.Date.to_date(value)

    if field.type == 'datetime':
        return odoo_fields.Datetime.to_datetime(value)

    if field.type == 'selection':
        return value

    return value
```

然后结合映射：

```python
def _prepare_dynamic_vals(self, data, mapping=None):
    vals = {}

    mapping = mapping or {}

    for external_key, value in data.items():
        odoo_field_name = mapping.get(external_key, external_key)

        field = self._fields.get(odoo_field_name)
        if not field:
            continue

        if field.compute and not field.inverse:
            continue

        vals[odoo_field_name] = self._convert_value_by_field_type(field, value)

    return vals
```

---

## 推荐的综合写法

如果你的字段很多、来源也比较复杂，可以这样封装一个通用 Mixin。

```python
from odoo import models, fields as odoo_fields


class DynamicFieldMappingMixin(models.AbstractModel):
    _name = 'dynamic.field.mapping.mixin'
    _description = 'Dynamic Field Mapping Mixin'

    def _get_dynamic_mapping(self):
        """
        子类可以重写这个方法。
        外部字段名 -> Odoo字段名
        """
        return {}

    def _is_writable_field(self, field_name, field):
        if field_name in ('id', 'create_uid', 'create_date', 'write_uid', 'write_date', '__last_update'):
            return False

        if field.compute and not field.inverse:
            return False

        if field.readonly:
            return False

        if field.type in ('one2many', 'many2many'):
            return False

        return True

    def _convert_dynamic_value(self, field, value):
        if value in (None, ''):
            return False

        if field.type == 'many2one':
            if isinstance(value, int):
                return value

            record = self.env[field.comodel_name].search([
                ('name', '=', value)
            ], limit=1)

            return record.id if record else False

        if field.type == 'integer':
            return int(value)

        if field.type == 'float':
            return float(value)

        if field.type == 'boolean':
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'y', '是')
            return bool(value)

        if field.type == 'date':
            return odoo_fields.Date.to_date(value)

        if field.type == 'datetime':
            return odoo_fields.Datetime.to_datetime(value)

        return value

    def _prepare_dynamic_vals(self, data):
        mapping = self._get_dynamic_mapping()
        vals = {}

        for external_key, value in data.items():
            field_name = mapping.get(external_key, external_key)
            field = self._fields.get(field_name)

            if not field:
                continue

            if not self._is_writable_field(field_name, field):
                continue

            vals[field_name] = self._convert_dynamic_value(field, value)

        return vals
```

业务模型继承：

```python
class YourModel(models.Model):
    _name = 'your.model'
    _inherit = ['dynamic.field.mapping.mixin']

    def _get_dynamic_mapping(self):
        return {
            '客户名称': 'name',
            '手机号': 'phone',
            '邮箱': 'email',
        }

    def import_data(self, data):
        vals = self._prepare_dynamic_vals(data)
        return self.create(vals)
```

---

## 性能优化建议

800+ 字段时，注意以下几点：

### 1. 不要每条数据都查 `ir.model.fields`

不推荐：

```python
for row in rows:
    fields = self.env['ir.model.fields'].search([...])
```

推荐提前缓存：

```python
field_names = set(self._fields.keys())
```

---

### 2. 批量 create

不要这样：

```python
for row in rows:
    vals = self._prepare_dynamic_vals(row)
    self.create(vals)
```

推荐：

```python
vals_list = []

for row in rows:
    vals_list.append(self._prepare_dynamic_vals(row))

self.create(vals_list)
```

---

### 3. Many2one 转换要做缓存

不要每次都 search：

```python
record = self.env['res.partner'].search([('name', '=', value)], limit=1)
```

建议缓存：

```python
m2o_cache = {}

def _get_many2one_id(self, model_name, name):
    key = (model_name, name)

    if key not in m2o_cache:
        record = self.env[model_name].search([('name', '=', name)], limit=1)
        m2o_cache[key] = record.id if record else False

    return m2o_cache[key]
```

---

## 最佳实践建议

对于你的情况，我建议采用：

```text
配置化字段映射模型
+
_fields 自动校验
+
按字段类型动态转换
+
批量 create/write
+
Many2one 缓存
```

如果外部字段名和 Odoo 字段名一致，则用：

```python
vals = {
    key: value
    for key, value in data.items()
    if key in self._fields
}
```

如果外部字段名不一致，则用：

```python
mapping = {
    '外部字段A': 'odoo_field_a',
    '外部字段B': 'odoo_field_b',
}
```

再动态转换即可。

---

## 简化版最终推荐代码

```python
def prepare_vals(self, data):
    vals = {}

    for key, value in data.items():
        field = self._fields.get(key)

        if not field:
            continue

        if field.compute and not field.inverse:
            continue

        if field.readonly:
            continue

        if field.type in ('one2many', 'many2many'):
            continue

        vals[key] = value

    return vals
```

创建：

```python
vals_list = [self.prepare_vals(row) for row in data_list]
records = self.env['your.model'].create(vals_list)
```

更新：

```python
for row in data_list:
    record = self.browse(row['id'])
    vals = self.prepare_vals(row)
    record.write(vals)
```

这样可以明显减少 800+ 字段带来的重复代码和维护成本。

# 其他优化方案

有。**800+ 字段的 Odoo 模型**，性能问题通常不只在“字段映射”，还会出现在：

- 数据库表太宽
- `read()` 读取字段过多
- Tree/Form 视图加载过多字段
- `compute` 字段过多或依赖链复杂
- `onchange` 太重
- `create/write` 触发大量逻辑
- `tracking=True` 太多
- `store=True` 计算字段太多
- `related` 字段泛滥
- `search` 域没有索引
- Many2one / One2many / Many2many 关系字段设计不合理
- 导入数据逐条 create/write

下面按方向给你一套比较系统的优化建议。

---

# 1. 首先判断：800+ 字段是否应该拆表

如果一个模型有 800 多个字段，第一反应应该是：**这个模型是否承载了太多业务含义？**

例如：

```text
customer.model
├── 基本信息字段 50 个
├── 财务字段 100 个
├── 资质字段 150 个
├── 风控字段 200 个
├── 合同字段 100 个
├── 审批字段 100 个
├── 扩展字段 100 个
```

这种情况下，不一定要都放在一个表里。

## 推荐拆分方式

### 方式一：按业务域拆成多个 One2one 子模型

Odoo 没有原生 One2one 字段，但可以用 `Many2one + unique constraint` 模拟。

```python
class MainModel(models.Model):
    _name = 'x.main.model'

    name = fields.Char()
    finance_id = fields.Many2one('x.main.finance', string='财务信息')
    risk_id = fields.Many2one('x.main.risk', string='风控信息')
```

子模型：

```python
class MainFinance(models.Model):
    _name = 'x.main.finance'

    main_id = fields.Many2one('x.main.model', required=True, ondelete='cascade')
    credit_limit = fields.Float()
    payment_term_id = fields.Many2one('account.payment.term')

    _sql_constraints = [
        ('main_unique', 'unique(main_id)', '每个主记录只能有一条财务信息')
    ]
```

也可以在主模型上做反向字段：

```python
finance_ids = fields.One2many('x.main.finance', 'main_id')
```

虽然技术上是 One2many，但用唯一约束保证只有一条。

### 适合拆出去的字段

建议拆分这些：

| 类型 | 是否建议拆出 |
|---|---|
| 极少使用的字段 | 强烈建议 |
| 某个页面 Tab 才用的字段 | 建议 |
| 大文本 Text / Html / Binary | 强烈建议 |
| 统计类字段 | 建议 |
| 审批历史类字段 | 强烈建议 |
| 外部系统同步字段 | 建议 |
| 临时字段 / 中间字段 | 强烈建议 |
| 业务扩展字段 | 建议 |

---

# 2. 大量字段时，避免默认读取所有字段

Odoo 的 `search()` 本身一般只返回记录集，不会把所有字段都读出来。

但下面这些操作容易触发字段读取：

```python
records.read()
records.export_data()
records.mapped('field_x')
for rec in records:
    rec.field_x
```

尤其是：

```python
records.read()
```

如果不指定字段，可能读取非常多字段。

## 不推荐

```python
records = self.search(domain)
data = records.read()
```

## 推荐

```python
records = self.search(domain)
data = records.read(['name', 'state', 'partner_id'])
```

或者更好：

```python
data = self.search_read(
    domain,
    fields=['name', 'state', 'partner_id'],
    limit=80
)
```

---

# 3. Tree / Form / Search 视图字段要控制

800+ 字段最容易让页面慢。

## Tree 视图不要放太多字段

尤其不要这样：

```xml
<tree>
    <field name="field_001"/>
    <field name="field_002"/>
    ...
    <field name="field_200"/>
</tree>
```

列表视图建议只放：

- 名称
- 状态
- 负责人
- 日期
- 金额
- 关键业务字段

例如：

```xml
<tree>
    <field name="name"/>
    <field name="state"/>
    <field name="user_id"/>
    <field name="create_date"/>
</tree>
```

## Form 视图使用 notebook 分页

```xml
<form>
    <sheet>
        <group>
            <field name="name"/>
            <field name="state"/>
        </group>

        <notebook>
            <page string="基础信息">
                <group>
                    <field name="field_a"/>
                    <field name="field_b"/>
                </group>
            </page>

            <page string="财务信息">
                <group>
                    <field name="credit_limit"/>
                    <field name="payment_term_id"/>
                </group>
            </page>

            <page string="扩展信息">
                <group>
                    <field name="field_x"/>
                    <field name="field_y"/>
                </group>
            </page>
        </notebook>
    </sheet>
</form>
```

不过注意：**notebook 分页不一定等于字段懒加载**。Form 打开时仍可能需要加载视图中出现的字段。所以字段太多时，拆模型比单纯分页更有效。

---

# 4. 减少 `compute` 字段数量和依赖链

大量字段模型里最危险的是这种：

```python
amount_total = fields.Float(compute='_compute_amount_total', store=True)
```

尤其是：

```python
@api.depends('line_ids.price_unit', 'line_ids.quantity', 'line_ids.discount')
def _compute_amount_total(self):
    ...
```

如果有几十上百个 `store=True compute` 字段，并且互相依赖，会让 `write()` 非常慢。

## 优化建议

### 1. 能不用 `store=True` 就不用

如果只是页面展示，且不用于搜索、排序、分组，可以：

```python
field_x = fields.Float(compute='_compute_field_x', store=False)
```

### 2. 需要搜索的字段才 store

适合 `store=True` 的场景：

- 需要 domain 搜索
- 需要 group_by
- 需要排序
- 报表频繁使用
- 值计算成本高但变化少

不适合 `store=True` 的场景：

- 只是表单展示
- 每次打开才看
- 依赖字段变化非常频繁
- 依赖链很长

### 3. 批量 compute，不要逐条查数据库

不推荐：

```python
@api.depends('partner_id')
def _compute_order_count(self):
    for rec in self:
        rec.order_count = self.env['sale.order'].search_count([
            ('partner_id', '=', rec.partner_id.id)
        ])
```

推荐：

```python
@api.depends('partner_id')
def _compute_order_count(self):
    partner_ids = self.mapped('partner_id').ids

    grouped = self.env['sale.order'].read_group(
        [('partner_id', 'in', partner_ids)],
        ['partner_id'],
        ['partner_id']
    )

    count_map = {
        item['partner_id'][0]: item['partner_id_count']
        for item in grouped
    }

    for rec in self:
        rec.order_count = count_map.get(rec.partner_id.id, 0)
```

---

# 5. 谨慎使用 `related` 字段

很多人会为了方便，在主模型上加大量 related：

```python
partner_phone = fields.Char(related='partner_id.phone', store=True)
partner_email = fields.Char(related='partner_id.email', store=True)
partner_street = fields.Char(related='partner_id.street', store=True)
partner_city = fields.Char(related='partner_id.city', store=True)
```

字段少还好，字段多会导致：

- 主表字段膨胀
- partner 修改时触发大量 recompute
- write 性能下降
- 模块升级字段同步慢

## 建议

如果只是展示，使用非存储 related：

```python
partner_phone = fields.Char(related='partner_id.phone', store=False)
```

如果要搜索，优先考虑直接通过关系字段搜索：

```python
domain = [('partner_id.phone', '=', phone)]
```

只有在报表、排序、分组、极高频查询时才考虑 `store=True`。

---

# 6. 给高频查询字段加索引

如果你的模型很大，而且经常按这些字段查：

```python
state
company_id
partner_id
user_id
date
active
external_id
code
```

建议加索引。

```python
state = fields.Selection([...], index=True)
partner_id = fields.Many2one('res.partner', index=True)
external_code = fields.Char(index=True)
```

如果是 SQL 层自定义索引：

```python
def init(self):
    self.env.cr.execute("""
        CREATE INDEX IF NOT EXISTS x_main_model_external_code_idx
        ON x_main_model (external_code)
    """)
```

组合索引示例：

```python
def init(self):
    self.env.cr.execute("""
        CREATE INDEX IF NOT EXISTS x_main_model_company_state_idx
        ON x_main_model (company_id, state)
    """)
```

适合组合索引的场景：

```python
[('company_id', '=', company_id), ('state', '=', state)]
```

---

# 7. 避免 `tracking=True` 泛滥

如果你的模型继承了：

```python
_inherit = ['mail.thread', 'mail.activity.mixin']
```

并且大量字段：

```python
field_a = fields.Char(tracking=True)
field_b = fields.Float(tracking=True)
field_c = fields.Selection(..., tracking=True)
```

那么每次 write 都可能产生大量 mail tracking 记录。

## 建议

只给关键字段加 tracking：

```python
state = fields.Selection([...], tracking=True)
amount_total = fields.Float(tracking=True)
user_id = fields.Many2one('res.users', tracking=True)
```

不要给 800 个字段都加。

如果批量导入时不需要 chatter，可以：

```python
records.with_context(
    tracking_disable=True,
    mail_notrack=True,
    mail_create_nolog=True
).write(vals)
```

创建时：

```python
self.with_context(
    tracking_disable=True,
    mail_create_nolog=True
).create(vals_list)
```

---

# 8. 批量 create / write，减少 ORM 循环

## 不推荐

```python
for row in rows:
    self.create(row)
```

## 推荐

```python
self.create(rows)
```

Odoo 支持批量 create：

```python
@api.model_create_multi
def create(self, vals_list):
    records = super().create(vals_list)
    return records
```

自定义 create 时一定用：

```python
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        vals['name'] = vals.get('name') or self.env['ir.sequence'].next_by_code('x.model')

    return super().create(vals_list)
```

不要写成：

```python
@api.model
def create(self, vals):
    return super().create(vals)
```

否则批量导入时性能会差很多。

---

# 9. 批量 write 时，按相同 vals 分组

如果每条记录写入值不同，只能循环：

```python
for rec, vals in zip(records, vals_list):
    rec.write(vals)
```

但如果很多记录写入相同状态：

```python
records.write({'state': 'done'})
```

比逐条写快很多。

如果 vals 有重复，可以分组：

```python
from collections import defaultdict

groups = defaultdict(list)

for record_id, vals in data:
    key = tuple(sorted(vals.items()))
    groups[key].append(record_id)

for key, ids in groups.items():
    vals = dict(key)
    self.browse(ids).write(vals)
```

---

# 10. 导入时关闭不必要的校验和副作用

如果是可信数据导入，可以适当用 context 控制。

```python
self.with_context(
    tracking_disable=True,
    mail_notrack=True,
    mail_create_nolog=True,
    prefetch_fields=False,
).create(vals_list)
```

但要谨慎使用：

```python
prefetch_fields=False
```

它可以减少预取字段，但某些业务逻辑依赖字段预取时，可能反而导致更多查询或逻辑问题。

---

# 11. 控制 prefetch，避免一次拉太多字段

Odoo ORM 有预取机制。访问一个字段时，可能会把同一批记录的该字段一起取出来。

通常这是好事，但在超大字段模型里，如果操作方式不当，可能会导致读取范围扩大。

## 推荐做法

只读必要字段：

```python
records.read(['id', 'name', 'state'])
```

处理大批数据时分批：

```python
limit = 1000
offset = 0

while True:
    records = self.search(domain, offset=offset, limit=limit, order='id')
    if not records:
        break

    # 处理 records

    offset += limit
```

更稳的方式是按 id 游标分页：

```python
last_id = 0
batch_size = 1000

while True:
    records = self.search([
        ('id', '>', last_id),
    ], order='id', limit=batch_size)

    if not records:
        break

    # 处理 records

    last_id = records[-1].id
```

---

# 12. One2many / Many2many 字段不要滥放在主视图

如果 Form 里有很多 One2many：

```xml
<field name="line_ids"/>
<field name="approval_ids"/>
<field name="log_ids"/>
<field name="history_ids"/>
```

打开表单会很慢。

## 优化方式

### 1. 给 One2many 加 limit

```xml
<field name="line_ids" limit="20"/>
```

### 2. 历史、日志类数据单独 action 打开

不要直接嵌在主表单：

```xml
<button name="action_open_logs" type="object" string="查看日志"/>
```

Python：

```python
def action_open_logs(self):
    self.ensure_one()
    return {
        'type': 'ir.actions.act_window',
        'name': '日志',
        'res_model': 'x.main.log',
        'view_mode': 'tree,form',
        'domain': [('main_id', '=', self.id)],
        'context': {'default_main_id': self.id},
    }
```

---

# 13. 大文本、JSON、二进制字段单独拆

这些字段非常容易拖慢主模型：

```python
raw_json = fields.Text()
description_html = fields.Html()
attachment_data = fields.Binary()
```

建议拆成附属模型：

```python
class MainPayload(models.Model):
    _name = 'x.main.payload'

    main_id = fields.Many2one('x.main.model', required=True, ondelete='cascade', index=True)
    payload_type = fields.Selection([
        ('request', '请求报文'),
        ('response', '响应报文'),
    ])
    content = fields.Text()
```

主模型只保留摘要：

```python
payload_count = fields.Integer(compute='_compute_payload_count')
```

---

# 14. 使用 SQL 视图做报表，不要在主模型堆统计字段

如果 800 字段中有很多是统计字段，例如：

```text
本月金额
本季度金额
本年金额
历史订单数
最近一次下单时间
最大逾期天数
```

建议不要全放在主模型上。

可以用 `_auto = False` 创建 SQL View 报表模型。

```python
class MainReport(models.Model):
    _name = 'x.main.report'
    _description = 'Main Report'
    _auto = False

    partner_id = fields.Many2one('res.partner')
    order_count = fields.Integer()
    amount_total = fields.Float()

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW x_main_report AS (
                SELECT
                    MIN(so.id) AS id,
                    so.partner_id AS partner_id,
                    COUNT(so.id) AS order_count,
                    SUM(so.amount_total) AS amount_total
                FROM sale_order so
                GROUP BY so.partner_id
            )
        """)
```

优点：

- 不污染主模型
- 查询报表更快
- 减少 recompute
- 减少 write 压力

---

# 15. 少用 `@api.onchange` 做重逻辑

字段很多时，`onchange` 会显著影响前端表单体验。

不推荐：

```python
@api.onchange('field_a')
def _onchange_field_a(self):
    orders = self.env['sale.order'].search([...])
    self.field_b = sum(orders.mapped('amount_total'))
```

推荐：

- onchange 只做轻量赋值
- 重计算放按钮
- 重计算放后端定时任务
- 重计算放 compute，但控制依赖
- 大数据查询用 `read_group`

---

# 16. 使用后台任务处理重逻辑

如果创建或更新一条记录后要同步很多字段、调用外部接口、生成报表，不要全部塞进 `write()`。

可以：

- 使用 cron 定时处理
- 使用队列模块，比如 OCA `queue_job`
- 使用异步 worker
- 使用状态字段标记待处理

示例：

```python
def write(self, vals):
    res = super().write(vals)

    if 'important_field' in vals:
        self.write({'need_recompute': True})

    return res
```

定时任务：

```python
def cron_recompute_large_fields(self):
    records = self.search([
        ('need_recompute', '=', True)
    ], limit=500)

    for rec in records:
        rec._recompute_large_fields()
        rec.need_recompute = False
```

---

# 17. 使用 JSON 字段承载低频扩展属性

如果 800 多字段中有大量“低频、不搜索、不排序、不统计”的扩展属性，可以考虑用 JSON 字段集中存。

例如：

```python
extra_data = fields.Json()
```

存储：

```python
record.extra_data = {
    'ext_field_001': 'value1',
    'ext_field_002': 'value2',
}
```

适合：

- 第三方系统原始扩展字段
- 很少用于 domain 的字段
- 只用于展示详情页
- 字段变化频繁，不想频繁升级模块

不适合：

- 需要经常搜索
- 需要权限控制
- 需要 group_by
- 需要 Odoo 标准字段视图编辑
- 需要导出成标准字段
- 需要字段级翻译

---

# 18. 避免在循环里访问关系字段造成 N+1 查询

不推荐：

```python
for rec in records:
    partner_name = rec.partner_id.name
    country_name = rec.partner_id.country_id.name
```

虽然 Odoo 有 prefetch，但复杂链路仍可能产生很多查询。

可以提前读取：

```python
records.read(['partner_id'])
partners = records.mapped('partner_id')
partners.read(['name', 'country_id'])
countries = partners.mapped('country_id')
countries.read(['name'])
```

或者用 `search_read` 直接取必要字段。

---

# 19. 用 `read_group` 替代循环统计

不推荐：

```python
for rec in records:
    rec.order_count = self.env['sale.order'].search_count([
        ('main_id', '=', rec.id)
    ])
```

推荐：

```python
grouped = self.env['sale.order'].read_group(
    [('main_id', 'in', records.ids)],
    ['main_id'],
    ['main_id']
)

count_map = {
    item['main_id'][0]: item['main_id_count']
    for item in grouped
}

for rec in records:
    rec.order_count = count_map.get(rec.id, 0)
```

---

# 20. 使用 `exists()` 过滤无效记录

大批量处理时，如果中间可能删除记录：

```python
records = records.exists()
```

避免后续访问报错或无效记录导致额外问题。

---

# 21. 对外部 ID / 编码字段建立唯一索引

如果你有外部系统同步场景：

```python
external_id = fields.Char(index=True)
```

建议加 SQL 唯一约束：

```python
_sql_constraints = [
    ('external_id_unique', 'unique(external_id)', '外部ID不能重复')
]
```

同步时可以快速定位：

```python
record = self.search([('external_id', '=', external_id)], limit=1)
```

如果没有索引，大表会很慢。

---

# 22. 避免频繁 `sudo()`

有些代码为了省事：

```python
self.env['x.main.model'].sudo().search(domain)
```

`sudo()` 会绕过规则，也可能改变缓存和权限行为。不是不能用，但不要无脑在循环里用。

不推荐：

```python
for row in rows:
    self.env['x.main.model'].sudo().create(row)
```

推荐：

```python
Model = self.env['x.main.model'].sudo()
Model.create(vals_list)
```

---

# 23. 对导入场景使用保存点

大批量导入时，一条失败不想影响全部，可以用 savepoint。

```python
for vals in vals_list:
    try:
        with self.env.cr.savepoint():
            self.create(vals)
    except Exception as e:
        _logger.exception("导入失败: %s", e)
```

但注意：逐条 savepoint 会有额外开销。数据可靠时，优先批量 create。

---

# 24. 减少自动序列调用次数

如果每条 create 都调用：

```python
self.env['ir.sequence'].next_by_code('x.model')
```

大量导入也会有成本。

可以只在没有传 name 时生成：

```python
@api.model_create_multi
def create(self, vals_list):
    seq = self.env['ir.sequence']

    for vals in vals_list:
        if not vals.get('name'):
            vals['name'] = seq.next_by_code('x.model')

    return super().create(vals_list)
```

---

# 25. 避免在 `write()` 里无条件重算所有字段

不推荐：

```python
def write(self, vals):
    res = super().write(vals)
    self._recompute_all_fields()
    return res
```

推荐：

```python
def write(self, vals):
    res = super().write(vals)

    if {'amount', 'quantity', 'discount'} & set(vals):
        self._recompute_amount_fields()

    if {'partner_id'} & set(vals):
        self._sync_partner_fields()

    return res
```

只在相关字段变化时执行逻辑。

---

# 26. 用字段白名单控制 create/write 逻辑触发

对于 800+ 字段模型，`write(vals)` 里一定要看 `vals` 里到底改了什么。

```python
FINANCE_FIELDS = {
    'credit_limit',
    'payment_term_id',
    'tax_id',
}

RISK_FIELDS = {
    'risk_level',
    'risk_score',
}

def write(self, vals):
    changed_fields = set(vals)

    res = super().write(vals)

    if changed_fields & FINANCE_FIELDS:
        self._after_finance_changed(vals)

    if changed_fields & RISK_FIELDS:
        self._after_risk_changed(vals)

    return res
```

---

# 27. 低频字段改为属性表 EAV，但要谨慎

如果字段极多，而且很多是动态属性，可以设计成：

```python
class MainAttributeValue(models.Model):
    _name = 'x.main.attribute.value'

    main_id = fields.Many2one('x.main.model', index=True, required=True)
    attribute_id = fields.Many2one('x.main.attribute', required=True)
    value_char = fields.Char()
    value_float = fields.Float()
    value_date = fields.Date()
```

优点：

- 不需要 800+ 真实列
- 动态扩展字段方便
- 低频属性适合

缺点：

- 查询复杂
- 搜索和排序性能不如真实字段
- 报表 SQL 更复杂
- Odoo 标准视图体验较差

所以，EAV 只适合真正“动态属性”场景，不建议替代所有业务字段。

---

# 28. 避免模型继承链太复杂

如果你的模型继承了很多 mixin：

```python
_inherit = [
    'mail.thread',
    'mail.activity.mixin',
    'portal.mixin',
    'utm.mixin',
    'rating.mixin',
]
```

每个 mixin 都可能带来字段、逻辑、消息、权限、compute。

建议只保留必须的。

---

# 29. 定期清理无用字段和无用索引

800+ 字段往往是长期迭代堆出来的。建议做字段盘点：

```python
self.env['ir.model.fields'].search([
    ('model', '=', 'x.main.model')
])
```

可以导出字段清单，标记：

- 是否在视图中使用
- 是否在代码中使用
- 是否在搜索中使用
- 是否有数据
- 是否需要索引
- 是否 compute
- 是否 tracking
- 是否 related
- 是否 store

长期无用字段可以：

- 先隐藏
- 再迁移
- 最后删除

---

# 30. 实用检查清单

你可以按这个顺序排查。

## 数据结构层

- [ ] 800+ 字段是否应该拆成多个子模型？
- [ ] 大 Text / Html / Binary 是否拆出？
- [ ] 低频扩展字段是否可放入 Json？
- [ ] 统计字段是否改成 SQL View 报表？
- [ ] 动态属性是否适合 EAV？

## ORM 层

- [ ] 是否批量 create？
- [ ] 自定义 create 是否用了 `@api.model_create_multi`？
- [ ] write 是否按字段变化触发逻辑？
- [ ] 是否避免了循环 search/search_count？
- [ ] 是否用 `read_group` 做统计？
- [ ] 是否只 read 必要字段？

## 字段层

- [ ] `compute store=True` 是否过多？
- [ ] `related store=True` 是否过多？
- [ ] `tracking=True` 是否过多？
- [ ] 高频 domain 字段是否有 index？
- [ ] Many2one 字段是否有 index？

## 视图层

- [ ] tree 是否字段过多？
- [ ] form 是否放了太多字段？
- [ ] One2many 是否加了 limit？
- [ ] 历史/日志是否独立 action 打开？
- [ ] search view 是否只放常用过滤字段？

## 数据库层

- [ ] 高频查询字段是否有索引？
- [ ] 高频组合 domain 是否有组合索引？
- [ ] 外部编码是否有唯一约束？
- [ ] 是否检查过慢 SQL？
- [ ] 是否做过 `EXPLAIN ANALYZE`？

---

# 我的建议

如果你这个模型已经有 **800+ 字段**，我会优先这样处理：

1. **字段分类**
   - 高频核心字段
   - 低频详情字段
   - 外部同步字段
   - 报表统计字段
   - 日志历史字段

2. **保留主模型核心字段**
   - 名称
   - 状态
   - 公司
   - 负责人
   - 日期
   - 关键金额
   - 关键业务索引字段

3. **低频字段拆子模型**
   - 财务详情
   - 风控详情
   - 扩展详情
   - 第三方同步详情

4. **报表字段改 SQL View**
5. **导入/同步逻辑做批量处理**
6. **compute / related / tracking 做瘦身**
7. **高频搜索字段加索引**

一句话总结：

> **800+ 字段模型的核心优化不是“怎么更快处理 800 个字段”，而是“尽量不要让每次操作都碰到这 800 个字段”。**