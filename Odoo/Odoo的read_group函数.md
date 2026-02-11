`read_group` 是 Odoo ORM（对象关系映射）中的一个强大方法，主要用于在数据库层面进行**分组聚合查询**。它类似于 SQL 中的 `GROUP BY` 操作，常用于统计、汇总、报表等场景。与 `search` 不同，`read_group` 直接返回分组后的结果，并且可以对某些字段做聚合（如计数、求和等）。

---

## 1. 作用简介

- **分组统计**：将记录按某字段分组，并对分组后的记录进行聚合运算（如计数、求和、平均值等）。
- **效率高**：直接在数据库层面处理，避免将大量数据拉到 Python 层再处理。

---

## 2. 基本用法

```python
Model.read_group(domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True)
```

- **domain**：筛选条件（与 search 一样）
- **fields**：需要读取和聚合的字段，例如 `['amount_total', 'amount_total:sum']`
- **groupby**：需要分组的字段（可以是字符串或列表）
- **offset, limit, orderby, lazy**：和 search 方法类似

---

## 3. 示例说明

### 例子：统计不同客户的订单总金额

假设你要统计每个客户的销售订单总金额，可以这样写：

```python
orders = self.env['sale.order'].read_group(
    domain=[('state', '=', 'sale')],                 # 已确认订单
    fields=['partner_id', 'amount_total:sum'],       # 统计总金额
    groupby=['partner_id'],                          # 按客户分组
)
```

#### 返回结果示例：

```python
[
    {
        'partner_id': (3, '客户A'),
        'amount_total': 25000.0,   # 该客户的订单总金额
        '__count': 4               # 该客户的订单数量
    },
    {
        'partner_id': (5, '客户B'),
        'amount_total': 18000.0,
        '__count': 2
    }
]
```

- `partner_id`：客户的 (id, name) 元组
- `amount_total`：分组后的总金额（sum）
- `__count`：该分组下的记录数

---

### 例子2：统计员工每月请假天数

```python
leaves = self.env['hr.leave'].read_group(
    domain=[('state', '=', 'validate')],
    fields=['employee_id', 'number_of_days:sum'],
    groupby=['employee_id', 'date_from:month'],  # 按员工和月份分组
)
```

---

## 4. 聚合方法

在 `fields` 字段里，支持如下聚合：

- `:sum`（求和）
- `:avg`（平均值）
- `:min`（最小值）
- `:max`（最大值）
- `:count`（计数）

---

## 5. 注意事项

- `read_group` 返回的是**分组后的字典列表**，不是 recordset。
- 如果分组字段是 many2one 类型，结果中是 (id, name) 形式。
- 适合用于做报表统计，不适合做复杂的数据处理。

---

## 6. 参考文档

- [Odoo官方文档：read_group](https://www.odoo.com/documentation/16.0/developer/reference/addons/orm.html#odoo.models.Model.read_group)

---

如需实际业务场景下的复杂分组或聚合示例，请告知你的业务字段和需求！