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

