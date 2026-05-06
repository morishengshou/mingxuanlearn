# odoo-llm 开发者指南

> **框架：** apexive/odoo-llm（Odoo 18.0）
> **文档版本：** 2026-05
> **适用读者：** 有 Odoo 开发基础，想为自己的模块接入 AI 能力的开发者

---

## 目录

1. [核心概念速览](#一核心概念速览)
2. [环境准备](#二环境准备)
3. [快速上手：第一个 AI 工具](#三快速上手第一个-ai-工具)
4. [@llm_tool 装饰器详解](#四llm_tool-装饰器详解)
5. [为现有模块添加 AI 对话](#五为现有模块添加-ai-对话)
6. [让 AI 读取业务数据](#六让-ai-读取业务数据)
7. [知识库（RAG）开发](#七知识库rag开发)
8. [自定义 AI 助手（Assistant）](#八自定义-ai-助手assistant)
9. [自定义 Provider（对接新模型）](#九自定义-provider对接新模型)
10. [完整示例：销售模块接入 AI](#十完整示例销售模块接入-ai)
11. [常见问题与调试](#十一常见问题与调试)

---

## 一、核心概念速览

### 框架分层结构

```
┌──────────────────────────────────────────────────────┐
│               你的业务模块 (your_module)               │
│   继承模型 + @llm_tool 装饰器 → AI 可调用的工具          │
└─────────────────────────┬────────────────────────────┘
                          │ 调用
┌─────────────────────────▼────────────────────────────┐
│          llm_assistant + llm_thread                  │
│   对话管理 / 助手配置 / 流式响应 / 工具调度              │
└─────────────────────────┬────────────────────────────┘
                          │ 调用
┌─────────────────────────▼────────────────────────────┐
│               llm (核心)                              │
│   Provider 抽象 / Model 管理 / 消息系统扩展             │
└─────────────────────────┬────────────────────────────┘
                          │ HTTP/SDK
┌─────────────────────────▼────────────────────────────┐
│         AI 推理服务（内网 vLLM / Ollama）               │
│         DeepSeek / GLM-4 / Qwen / Llama3 等           │
└──────────────────────────────────────────────────────┘
```

### 五大核心模型

| 模型 | 说明 |
|------|------|
| `llm.provider` | AI 服务提供商配置（URL、API Key、服务类型） |
| `llm.model` | AI 模型实例（绑定到 Provider，指定用途：chat/embedding） |
| `llm.thread` | 对话线程，继承自 `mail.thread`，存储消息历史 |
| `llm.assistant` | AI 助手配置（关联 Provider、工具集、系统提示词） |
| `llm.tool` | 工具注册表，`@llm_tool` 装饰的方法自动注册到此 |

### 消息角色（llm_role）

`mail.message` 被扩展了 `llm_role` 字段，取值：

| 角色 | 含义 |
|------|------|
| `user` | 用户发送的消息 |
| `assistant` | AI 生成的回复 |
| `tool` | 工具调用结果（存储在 `body_json` 字段） |
| `system` | 系统提示词消息 |

---

## 二、环境准备

### 模块依赖声明

在你的模块 `__manifest__.py` 中声明依赖：

```python
# your_module/__manifest__.py
{
    'name': 'Your Module with AI',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'llm',          # 核心依赖（必须）
        'llm_tool',     # 如果要添加工具（通常必须）
        'llm_thread',   # 如果要嵌入对话界面
        'llm_assistant', # 如果要使用助手功能
        # 'llm_knowledge', # 如果要使用 RAG
        # 'sale',         # 你的业务模块依赖
    ],
    'installable': True,
}
```

### Python 依赖

无需额外 pip 包——`@llm_tool` 装饰器只依赖框架自身。如果要开发自定义 Provider，才需要对应 SDK。

---

## 三、快速上手：第一个 AI 工具

最快接入 AI 能力的方式：用 `@llm_tool` 装饰器给现有模型添加一个方法。

### 3.1 创建工具文件

```python
# your_module/models/sale_order.py
import logging
from odoo import models
from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @llm_tool(read_only_hint=True)
    def get_order_summary(self, order_id: int) -> dict:
        """获取销售订单摘要

        查询指定销售订单的基本信息，包括客户、金额、状态和产品列表。

        Args:
            order_id: 销售订单的数据库 ID

        Returns:
            包含订单摘要信息的字典
        """
        order = self.browse(order_id)
        if not order.exists():
            return {"error": f"订单 ID {order_id} 不存在"}

        return {
            "id": order.id,
            "name": order.name,
            "customer": order.partner_id.name,
            "amount_total": order.amount_total,
            "currency": order.currency_id.name,
            "state": order.state,
            "date_order": str(order.date_order),
            "lines": [
                {
                    "product": line.product_id.name,
                    "qty": line.product_uom_qty,
                    "price_unit": line.price_unit,
                    "subtotal": line.price_subtotal,
                }
                for line in order.order_line
            ],
        }
```

### 3.2 注册到 `__init__.py`

```python
# your_module/models/__init__.py
from . import sale_order
```

### 3.3 安装后在后台激活工具

1. 进入 **AI → 工具（Tools）** 菜单
2. 找到 `sale_order.get_order_summary`（框架自动注册）
3. 在 **助手（Assistant）** 中的 **工具** 标签页勾选它

**就这三步，AI 助手就能调用你的工具读取销售订单了。**

---

## 四、`@llm_tool` 装饰器详解

### 4.1 装饰器参数

```python
from odoo.addons.llm_tool.decorators import llm_tool

@llm_tool(
    read_only_hint=True,        # True: 只读操作（不修改数据）
    destructive_hint=False,     # True: 可能产生不可逆操作（删除等）
    idempotent_hint=True,       # True: 多次调用同样参数结果相同
    open_world_hint=False,      # True: 可能与外部系统交互
    requires_user_consent=False, # True: 执行前需要用户确认
    schema=None,                # 手动指定 JSON Schema（不用类型注解时使用）
)
def my_tool(self, param: str) -> dict:
    ...
```

### 4.2 参数类型与 JSON Schema 自动生成

框架通过 **Python 类型注解** 自动生成 JSON Schema，无需手写：

```python
@llm_tool(read_only_hint=True)
def search_partners(
    self,
    keyword: str,               # → {"type": "string"}
    limit: int = 10,            # → {"type": "integer"}，有默认值则非必填
    include_inactive: bool = False,  # → {"type": "boolean"}
    categories: list = None,    # → {"type": "array"}
) -> dict:
    """搜索合作伙伴

    Args:
        keyword: 搜索关键词（姓名或邮箱）
        limit: 最多返回数量，默认 10
        include_inactive: 是否包含已归档的合作伙伴
        categories: 过滤的分类列表（可选）

    Returns:
        匹配的合作伙伴列表
    """
    domain = ["|", ("name", "ilike", keyword), ("email", "ilike", keyword)]
    if not include_inactive:
        domain.append(("active", "=", True))

    partners = self.env["res.partner"].search(domain, limit=limit)
    return {
        "count": len(partners),
        "partners": [
            {"id": p.id, "name": p.name, "email": p.email}
            for p in partners
        ],
    }
```

### 4.3 无类型注解时手动指定 Schema

适用于需要复用已有方法、或参数类型复杂的场景：

```python
@llm_tool(
    read_only_hint=True,
    schema={
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Odoo 模型技术名称，例如 'res.partner'",
            },
            "domain": {
                "type": "array",
                "description": "Odoo domain 查询条件",
                "items": {}
            },
        },
        "required": ["model_name"],
    }
)
def generic_search(self, model_name, domain=None):
    """通用记录搜索（演示手动 schema）"""
    records = self.env[model_name].search(domain or [])
    return {"count": len(records), "ids": records.ids}
```

### 4.4 工具方法的最佳实践

```python
@llm_tool(destructive_hint=True)
def create_task(
    self,
    name: str,
    project_name: str,
    description: str = "",
    assignee_name: str = "",
) -> dict:
    """创建项目任务

    Args:
        name: 任务名称
        project_name: 项目名称（精确匹配）
        description: 任务描述（可选）
        assignee_name: 负责人姓名（可选）

    Returns:
        已创建的任务信息
    """
    from odoo.exceptions import UserError

    # 1. 参数验证要在最前面
    project = self.env["project.project"].search(
        [("name", "=", project_name)], limit=1
    )
    if not project:
        raise UserError(f"项目 '{project_name}' 不存在")  # AI 会看到这个错误

    # 2. 处理可选参数
    vals = {"name": name, "project_id": project.id, "description": description}
    if assignee_name:
        user = self.env["res.users"].search([("name", "ilike", assignee_name)], limit=1)
        if user:
            vals["user_ids"] = [(4, user.id)]

    # 3. 执行操作
    task = self.env["project.task"].create(vals)

    # 4. 返回 JSON 可序列化的字典（不要返回 Recordset）
    return {
        "task_id": task.id,
        "task_name": task.name,
        "project": project.name,
        "assignee": task.user_ids[0].name if task.user_ids else None,
        "url": f"/odoo/project/{project.id}/task/{task.id}",
    }
```

**关键原则：**
- ✅ 尽早校验参数，用 `UserError` 抛出友好错误（AI 会把错误信息传回给用户）
- ✅ 返回 `dict`，所有值必须是 JSON 可序列化类型（str / int / float / bool / list / dict）
- ❌ 不要返回 Recordset 对象
- ❌ 不要在 `dict` 中放 `datetime` 对象，转为 `str(dt)` 或 `.isoformat()`
- ✅ Docstring 的 `Args` 段落会被发给 AI，要写得清晰准确

---

## 五、为现有模块添加 AI 对话

将 AI 对话界面嵌入到你的模块表单视图，让用户可以在业务记录旁边与 AI 交谈。

### 5.1 Python：在业务模型上创建对话线程

```python
# your_module/models/your_model.py
from odoo import fields, models


class YourModel(models.Model):
    _name = "your.model"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Your Model"

    name = fields.Char(required=True)
    # ... 其他业务字段 ...

    def action_open_ai_chat(self):
        """打开与当前记录关联的 AI 对话界面"""
        self.ensure_one()

        # 查找或创建关联到本记录的对话线程
        thread = self.env["llm.thread"].search(
            [
                ("model", "=", self._name),
                ("res_id", "=", self.id),
            ],
            limit=1,
        )

        if not thread:
            # 获取默认的助手（或由用户选择）
            assistant = self.env["llm.assistant"].search([], limit=1)
            if not assistant:
                from odoo.exceptions import UserError
                raise UserError("请先配置至少一个 AI 助手")

            thread = self.env["llm.thread"].create(
                {
                    "name": f"AI 助手 - {self.display_name}",
                    "assistant_id": assistant.id,
                    "model": self._name,   # 关联到当前模型
                    "res_id": self.id,     # 关联到当前记录
                }
            )

        # 跳转到对话线程视图
        return {
            "type": "ir.actions.act_window",
            "name": "AI 对话",
            "res_model": "llm.thread",
            "res_id": thread.id,
            "view_mode": "form",
            "target": "new",
        }
```

### 5.2 XML：在表单视图添加按钮

```xml
<!-- your_module/views/your_model_views.xml -->
<odoo>
    <record id="view_your_model_form" model="ir.ui.view">
        <field name="name">your.model.form</field>
        <field name="model">your.model</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <!-- 在表单头部添加 AI 按钮 -->
                    <button
                        name="action_open_ai_chat"
                        type="object"
                        string="💬 AI 助手"
                        class="oe_highlight"
                    />
                </header>
                <sheet>
                    <field name="name"/>
                    <!-- ... 其他字段 ... -->
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        </field>
    </record>
</odoo>
```

### 5.3 让 AI 自动感知当前业务记录

通过 Assistant 的 **系统提示词（System Prompt）** 注入当前记录的上下文：

在 **AI → 助手** 中配置系统提示词，使用 Jinja2 模板语法：

```jinja2
你是一个专业的业务助手。

当前正在处理的记录：
- 模型：{{ related_model }}
- 记录名称：{{ related_record.display_name }}
- 记录 ID：{{ related_res_id }}

你可以使用提供的工具查询和操作相关数据。
请用中文回答用户的问题，保持专业和简洁。
```

---

## 六、让 AI 读取业务数据

### 6.1 基础模式：单记录查询

```python
# your_module/models/project_task.py
from odoo import models
from odoo.addons.llm_tool.decorators import llm_tool


class ProjectTask(models.Model):
    _inherit = "project.task"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def get_task_details(self, task_id: int) -> dict:
        """获取项目任务的详细信息

        Args:
            task_id: 任务 ID

        Returns:
            任务的完整信息，包括状态、截止日期、负责人和子任务
        """
        task = self.browse(task_id)
        if not task.exists():
            return {"error": f"任务 ID {task_id} 不存在"}

        return {
            "id": task.id,
            "name": task.name,
            "project": task.project_id.name if task.project_id else None,
            "stage": task.stage_id.name if task.stage_id else None,
            "priority": task.priority,
            "assignees": [u.name for u in task.user_ids],
            "deadline": str(task.date_deadline) if task.date_deadline else None,
            "description": task.description or "",
            "subtask_count": task.child_count,
            "progress": task.progress,
        }
```

### 6.2 进阶模式：聚合统计查询

```python
@llm_tool(read_only_hint=True, idempotent_hint=True)
def get_project_statistics(
    self,
    project_name: str,
    date_from: str = "",
    date_to: str = "",
) -> dict:
    """获取项目统计数据

    Args:
        project_name: 项目名称（支持模糊匹配）
        date_from: 开始日期，格式 YYYY-MM-DD（可选）
        date_to: 结束日期，格式 YYYY-MM-DD（可选）

    Returns:
        项目的任务统计、完成率、工时等汇总数据
    """
    projects = self.env["project.project"].search(
        [("name", "ilike", project_name)]
    )
    if not projects:
        return {"error": f"未找到名称包含 '{project_name}' 的项目"}

    result = []
    for project in projects:
        domain = [("project_id", "=", project.id)]
        if date_from:
            domain.append(("create_date", ">=", date_from))
        if date_to:
            domain.append(("create_date", "<=", date_to))

        tasks = self.env["project.task"].search(domain)
        done_tasks = tasks.filtered(lambda t: t.stage_id.fold)

        result.append({
            "project_id": project.id,
            "project_name": project.name,
            "total_tasks": len(tasks),
            "done_tasks": len(done_tasks),
            "completion_rate": (
                round(len(done_tasks) / len(tasks) * 100, 1) if tasks else 0
            ),
            "overdue_tasks": len(
                tasks.filtered(
                    lambda t: t.date_deadline and t.date_deadline < fields.Date.today()
                )
            ),
        })

    return {"projects": result, "total_projects": len(result)}
```

### 6.3 写操作模式：创建/更新记录

```python
@llm_tool(destructive_hint=True)
def update_task_stage(self, task_id: int, stage_name: str) -> dict:
    """更新任务阶段

    将指定任务移动到目标阶段。

    Args:
        task_id: 任务 ID
        stage_name: 目标阶段名称（如"进行中"、"已完成"）

    Returns:
        更新结果，包含任务名称和新阶段
    """
    from odoo.exceptions import UserError

    task = self.browse(task_id)
    if not task.exists():
        raise UserError(f"任务 ID {task_id} 不存在")

    # 在同一项目内查找阶段
    stage = self.env["project.task.type"].search(
        [
            ("name", "ilike", stage_name),
            ("project_ids", "in", [task.project_id.id]),
        ],
        limit=1,
    )
    if not stage:
        # 返回可用阶段供 AI 提示用户
        available = self.env["project.task.type"].search(
            [("project_ids", "in", [task.project_id.id])]
        ).mapped("name")
        raise UserError(
            f"阶段 '{stage_name}' 不存在。可用阶段：{', '.join(available)}"
        )

    old_stage = task.stage_id.name
    task.write({"stage_id": stage.id})

    return {
        "success": True,
        "task_id": task_id,
        "task_name": task.name,
        "old_stage": old_stage,
        "new_stage": stage.name,
    }
```

---

## 七、知识库（RAG）开发

让 AI 能够检索你的内部文档，实现"问文档"功能。

### 7.1 依赖配置

```python
# __manifest__.py
'depends': ['llm', 'llm_knowledge', 'llm_pgvector', 'llm_tool_knowledge'],
```

### 7.2 编程方式创建知识资源

```python
def index_document_for_rag(self):
    """将当前记录的文档内容索引到知识库"""
    self.ensure_one()

    # 查找或创建对应的知识集合（Collection）
    collection = self.env["llm.knowledge.collection"].search(
        [("name", "=", "内部文档库")], limit=1
    )
    if not collection:
        collection = self.env["llm.knowledge.collection"].create(
            {"name": "内部文档库"}
        )

    # 创建资源记录（关联到当前模型记录）
    resource = self.env["llm.resource"].create(
        {
            "name": self.display_name,
            "collection_id": collection.id,
            "model": self._name,
            "res_id": self.id,
            "retrieval_type": "field",        # 从字段读取内容
            "retrieval_details": "description",  # 读取 description 字段
        }
    )

    # 触发处理流水线：draft → retrieved → parsed → chunked → ready
    resource.process_resource()
    return resource
```

### 7.3 在工具中使用 RAG 检索

```python
@llm_tool(read_only_hint=True, idempotent_hint=True)
def search_internal_docs(self, query: str, limit: int = 5) -> dict:
    """检索内部知识库文档

    在公司内部文档中搜索与问题相关的内容。

    Args:
        query: 搜索问题或关键词
        limit: 返回最相关的文档片段数量，默认 5

    Returns:
        相关文档片段列表，包含来源信息和相关度分数
    """
    # 获取知识检索工具（llm_tool_knowledge 提供）
    store = self.env["llm.store"].search([], limit=1)
    if not store:
        return {"error": "未配置向量存储"}

    # 获取 Embedding 并检索
    results = store.search(query=query, collection="内部文档库", limit=limit)

    return {
        "query": query,
        "results": [
            {
                "content": r.get("content", ""),
                "source": r.get("metadata", {}).get("source_name", "未知"),
                "score": round(r.get("score", 0), 3),
            }
            for r in results
        ],
    }
```

---

## 八、自定义 AI 助手（Assistant）

### 8.1 用代码创建助手（适合模块初始化数据）

```xml
<!-- your_module/data/llm_assistant_data.xml -->
<odoo>
    <record id="assistant_sales_helper" model="llm.assistant">
        <field name="name">销售助手</field>
        <field name="active">True</field>
        <!-- system_prompt 使用 Jinja2 模板 -->
        <field name="system_prompt">你是一个专业的销售助手，帮助销售团队处理客户咨询、查询订单状态和分析销售数据。

当前日期：{{ current_date }}
当前用户：{{ user.name }}
{% if related_record %}
当前查看的记录：{{ related_record.display_name }}
{% endif %}

请始终使用中文回答，保持专业、简洁的风格。</field>
    </record>
</odoo>
```

### 8.2 用 Python 代码创建助手

```python
def _create_default_assistant(self):
    """在模块安装时创建默认助手"""
    # 获取默认 Provider
    provider = self.env["llm.provider"].search(
        [("service", "=", "openai")], limit=1
    )
    if not provider:
        return

    # 获取 chat 类型的默认模型
    model = self.env["llm.model"].search(
        [("provider_id", "=", provider.id), ("model_use", "=", "chat")],
        limit=1,
    )

    # 获取相关工具
    tools = self.env["llm.tool"].search(
        [("decorator_model", "in", ["sale.order", "res.partner"])]
    )

    assistant = self.env["llm.assistant"].create(
        {
            "name": "销售智能助手",
            "provider_id": provider.id,
            "model_id": model.id,
            "tool_ids": [(6, 0, tools.ids)],
            "system_prompt": "你是专业的销售助手...",
        }
    )
    return assistant
```

---

## 九、自定义 Provider（对接新模型）

如果内网部署的模型使用 **OpenAI 兼容协议**（如 vLLM、Ollama API、GLM-4、DeepSeek），**无需开发新 Provider**，直接用 `llm_openai` 模块配置 `api_base` 即可。

只有当模型使用**完全不同的 API 协议**时，才需要自定义 Provider。

### 9.1 新建 Provider 模块结构

```
llm_my_provider/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── my_provider.py
└── data/
    └── llm_provider_data.xml
```

### 9.2 `__manifest__.py`

```python
{
    'name': 'LLM My Provider',
    'version': '18.0.1.0.0',
    'depends': ['llm'],
    'data': ['data/llm_provider_data.xml'],
    'installable': True,
    'license': 'LGPL-3',
}
```

### 9.3 Provider 实现

```python
# llm_my_provider/models/my_provider.py
import logging
import requests
from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        """注册新的服务类型"""
        return super()._get_available_services() + [("myprovider", "My Provider")]

    # ---- 客户端初始化 ----

    def myprovider_get_client(self):
        """创建 API 客户端（这里用 requests.Session 示意）"""
        self.ensure_one()
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        return session

    # ---- 核心方法：chat ----

    def myprovider_chat(self, messages, model=None, stream=False, **kwargs):
        """实现 chat 接口

        Args:
            messages: mail.message recordset
            model: llm.model 记录
            stream: 是否流式返回
        Returns:
            非流式: dict {"content": str}
            流式:   generator, 每次 yield dict {"content": str_chunk}
        """
        model = self.get_model(model, "chat")
        formatted = self.format_messages(messages, model=model)

        payload = {
            "model": model.name,
            "messages": formatted,
            "stream": stream,
        }

        base_url = (self.api_base or "http://localhost:8080").rstrip("/")
        url = f"{base_url}/v1/chat/completions"

        if stream:
            return self._myprovider_stream(url, payload)
        else:
            resp = self.client.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return {"content": data["choices"][0]["message"]["content"]}

    def _myprovider_stream(self, url, payload):
        """流式生成器"""
        import json
        with self.client.post(url, json=payload, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line and line.startswith(b"data: "):
                    chunk = line[6:]
                    if chunk == b"[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            yield {"content": delta["content"]}
                    except (json.JSONDecodeError, KeyError):
                        continue

    # ---- 可选方法：embedding ----

    def myprovider_embedding(self, texts, model=None, **kwargs):
        """实现 embedding 接口（可选）"""
        model = self.get_model(model, "embedding")
        base_url = (self.api_base or "http://localhost:8080").rstrip("/")
        url = f"{base_url}/v1/embeddings"

        resp = self.client.post(
            url,
            json={"model": model.name, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

    # ---- 可选方法：models ----

    def myprovider_models(self, model_id=None):
        """列出可用模型（用于同步按钮）"""
        base_url = (self.api_base or "http://localhost:8080").rstrip("/")
        resp = self.client.get(f"{base_url}/v1/models", timeout=30)
        resp.raise_for_status()
        for m in resp.json().get("data", []):
            yield {
                "name": m["id"],
                "details": {"id": m["id"], "capabilities": ["chat"]},
            }
```

### 9.4 命名规则说明

框架通过 `_dispatch()` 动态路由，命名必须遵循 `{service}_{method}` 格式：

| 方法名 | 说明 | 必须实现 |
|--------|------|---------|
| `{svc}_get_client` | 创建客户端实例 | ✅ |
| `{svc}_chat` | 对话接口 | ✅（chat 功能） |
| `{svc}_embedding` | 向量嵌入接口 | 可选 |
| `{svc}_models` | 列出模型 | 可选（同步按钮） |
| `{svc}_generate` | 图像/内容生成 | 可选 |
| `{svc}_format_messages` | 自定义消息格式化 | 可选 |
| `{svc}_format_tools` | 自定义工具格式化 | 可选 |

---

## 十、完整示例：销售模块接入 AI

以下是一个完整的迷你模块，演示如何为销售订单添加 AI 能力。

### 目录结构

```
llm_sale_helper/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── sale_order.py
├── views/
│   └── sale_order_views.xml
└── data/
    └── llm_assistant_data.xml
```

### `__manifest__.py`

```python
{
    'name': 'LLM Sale Helper',
    'version': '18.0.1.0.0',
    'depends': ['sale', 'llm', 'llm_tool', 'llm_thread', 'llm_assistant'],
    'data': [
        'views/sale_order_views.xml',
        'data/llm_assistant_data.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
```

### `models/sale_order.py`

```python
import logging
from odoo import models
from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @llm_tool(read_only_hint=True)
    def get_order_summary(self, order_id: int) -> dict:
        """获取销售订单摘要，包含客户信息、金额和产品列表"""
        order = self.browse(order_id)
        if not order.exists():
            return {"error": f"订单 {order_id} 不存在"}
        return {
            "name": order.name,
            "customer": order.partner_id.name,
            "amount": order.amount_total,
            "currency": order.currency_id.name,
            "state": order.state,
            "lines": [
                {"product": l.product_id.name, "qty": l.product_uom_qty}
                for l in order.order_line
            ],
        }

    @llm_tool(read_only_hint=True)
    def find_orders_by_customer(self, customer_name: str, limit: int = 5) -> dict:
        """按客户名称查找销售订单"""
        partners = self.env["res.partner"].search(
            [("name", "ilike", customer_name)]
        )
        orders = self.search(
            [("partner_id", "in", partners.ids), ("state", "!=", "cancel")],
            limit=limit, order="date_order desc",
        )
        return {
            "count": len(orders),
            "orders": [
                {"id": o.id, "name": o.name, "date": str(o.date_order)[:10],
                 "amount": o.amount_total, "state": o.state}
                for o in orders
            ],
        }

    def action_open_ai_chat(self):
        """打开当前订单的 AI 助手对话"""
        self.ensure_one()
        thread = self.env["llm.thread"].search(
            [("model", "=", self._name), ("res_id", "=", self.id)], limit=1
        )
        if not thread:
            assistant = self.env.ref(
                "llm_sale_helper.assistant_sale_helper", raise_if_not_found=False
            )
            thread = self.env["llm.thread"].create({
                "name": f"AI - {self.name}",
                "assistant_id": assistant.id if assistant else False,
                "model": self._name,
                "res_id": self.id,
            })
        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.thread",
            "res_id": thread.id,
            "view_mode": "form",
            "target": "new",
        }
```

### `views/sale_order_views.xml`

```xml
<odoo>
    <record id="view_sale_order_form_ai" model="ir.ui.view">
        <field name="name">sale.order.form.ai</field>
        <field name="model">sale.order</field>
        <field name="inherit_id" ref="sale.view_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//header/button[last()]" position="after">
                <button name="action_open_ai_chat" type="object"
                        string="🤖 AI 助手" class="oe_highlight"/>
            </xpath>
        </field>
    </record>
</odoo>
```

### `data/llm_assistant_data.xml`

```xml
<odoo>
    <record id="assistant_sale_helper" model="llm.assistant">
        <field name="name">销售订单助手</field>
        <field name="system_prompt">
你是一个专业的销售助手。
{% if related_record %}
当前订单：{{ related_record.name }}
客户：{{ related_record.partner_id.name }}
金额：{{ related_record.amount_total }} {{ related_record.currency_id.name }}
状态：{{ related_record.state }}
{% endif %}

你可以使用工具查询订单详情和客户历史记录。请用中文回答。
        </field>
    </record>
</odoo>
```

---

## 十一、常见问题与调试

### Q1：工具注册后在后台看不到？

**原因：** 模块未安装或 Python 文件未加入 `__init__.py`。

**排查：**
```bash
# 重启 Odoo 并更新模块
odoo-bin -d your_db -u your_module --stop-after-init
```

查看日志是否有 `llm_tool` 注册相关输出。

### Q2：AI 调用工具时报错 "Tool not found"？

**原因：** 助手配置中没有勾选该工具。

**解决：** 进入 **AI → 助手 → 编辑 → 工具标签页**，勾选对应工具并保存。

### Q3：工具返回值 AI 看不懂？

**原因：** 返回了不可 JSON 序列化的对象（如 `datetime`、`Recordset`）。

**解决：**
```python
# ❌ 错误
return {"date": order.date_order}  # datetime 对象

# ✅ 正确
return {"date": str(order.date_order)[:10]}  # 转为字符串
```

### Q4：对话线程与业务记录关联后，System Prompt 里的变量为空？

**原因：** 创建 `llm.thread` 时没有设置 `model` 和 `res_id` 字段。

**解决：**
```python
# ✅ 必须同时设置这两个字段
thread = self.env["llm.thread"].create({
    "name": "...",
    "assistant_id": assistant.id,
    "model": self._name,   # 例如 "sale.order"
    "res_id": self.id,     # 记录的 ID
})
```

### Q5：流式响应没有实时显示？

**原因：** 浏览器与 Odoo 之间缺少 `EventSource` 支持，或反向代理配置了 buffer。

**Nginx 解决：**
```nginx
location / {
    proxy_pass http://127.0.0.1:8069;
    proxy_buffering off;           # 关闭 buffer，支持 SSE 流
    proxy_cache off;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 300s;       # 增加超时（流式响应可能较长）
}
```

---

*参考资源：*
- *[GitHub 仓库](https://github.com/apexive/odoo-llm)*
- *[Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/llm)*
- *[Apexive 案例介绍](https://apexive.com/projects/odoo-llm-framework)*
