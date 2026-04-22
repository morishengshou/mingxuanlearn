# Odoo 18 社区版本地 AI 能力接入方案

下面是一份完整的落地方案，结合你的本地部署 Qwen / GLM 模型和 Odoo 18 CE 的特点。

## 一、整体架构建议

```
┌──────────────────────────────────────────────────────────┐
│                    Odoo 18 Community                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  llm (base) │→│ llm_thread   │→│ llm_assistant   │  │
│  │             │  │ (聊天 UI)    │  │ (预设 Prompt)   │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│         ↓                                    ↓           │
│  ┌─────────────────┐              ┌─────────────────┐    │
│  │ llm_knowledge   │              │  llm_tool       │    │
│  │ (RAG 知识库)    │              │ (函数调用)      │    │
│  └─────────────────┘              └─────────────────┘    │
│         ↓                                                │
│  ┌─────────────────────────────────────────────┐         │
│  │ llm_ollama / llm_openai_compatible (Provider)│        │
│  └─────────────────────────────────────────────┘         │
└────────────────────────────┬─────────────────────────────┘
                             │ OpenAI-compatible HTTP
                             ▼
           ┌──────────────────────────────────┐
           │ 本地模型服务 (vLLM / Ollama /     │
           │ Xinference / FastChat)            │
           │  - Qwen2.5 / Qwen3               │
           │  - GLM-4 / ChatGLM3              │
           │  - bge-m3 (Embedding)            │
           └──────────────────────────────────┘
```

## 二、推荐模块（首选：apexive 的 odoo-llm 生态）

这是目前 Odoo 18 上最成熟、最模块化的开源 AI 框架，非常适合你这种本地化、私有部署的需求。

### 1. 核心基座
- **`llm` (LLM Integration Base)**：统一框架，用于连接各种 AI 提供商和模型，提供聊天补全、文本嵌入、模型管理、工具调用（function calling）等基础能力[[3]](https://apps.odoo.com/apps/modules/16.0/llm)。所有其他模块都依赖它。

### 2. 对话与 UI 层
- **`llm_thread` (Easy AI Chat)**：为 Odoo 提供实时 AI 聊天界面，支持流式响应、工具执行，并与 Odoo 的 mail 系统无缝集成[[4]](https://apps.odoo.com/apps/modules/18.0/llm_thread)。消息存储在 mail.message 中并带有 llm_role 字段，使用 PostgreSQL advisory locks 防止并发生成[[4]](https://apps.odoo.com/apps/modules/18.0/llm_thread)。
- **`llm_assistant`**：创建带有自定义 prompt 和角色设定的专用 AI 助手[[2]](https://apps.odoo.com/apps/modules/18.0/llm_ollama)，用于"销售助手"、"采购分析师"等场景。

### 3. 知识库问答（RAG）—— 满足你"知识库问答"需求
- **`llm_knowledge`**：基于 RAG 的知识库，支持语义搜索和文档索引[[2]](https://apps.odoo.com/apps/modules/18.0/llm_ollama)；可基于 Odoo 数据库中的知识增强 AI 响应，创建文档集合、生成 embedding、实现语义搜索[[3]](https://apps.odoo.com/apps/modules/16.0/llm)。

### 4. 函数调用 —— 满足你"指令总结/执行"需求
- **`llm_tool`**：通过 @llm_tool 装饰器让 AI 执行 Odoo 函数[[2]](https://apps.odoo.com/apps/modules/18.0/llm_ollama)[[4]](https://apps.odoo.com/apps/modules/18.0/llm_thread)。实现函数调用能力，让 AI 通过标准化工具执行框架在 Odoo 中执行操作[[3]](https://apps.odoo.com/apps/modules/16.0/llm)。

### 5. 本地模型 Provider（关键 —— 你的 Qwen / GLM 接入点）
你有两种选择：

**方案 A：通过 Ollama（推荐，部署最简单）**
- **`llm_ollama`**：扩展 LLM Integration Base 以连接本地部署的 Ollama 模型，让你在 Odoo 实例中直接使用开源模型，数据完全不离开服务器[[2]](https://apps.odoo.com/apps/modules/18.0/llm_ollama)。Ollama 已支持 Qwen 全系列和 GLM-4。

**方案 B：通过 OpenAI 兼容接口（推荐用于 vLLM / Xinference）**
- **`llm_openai_compatible`**：连接 OpenAI、Gemini、Grok、DeepSeek 以及任何 OpenAI 兼容的 API[[2]](https://apps.odoo.com/apps/modules/18.0/llm_ollama)。vLLM、Xinference、FastChat 部署的 Qwen/GLM 默认都暴露 OpenAI 兼容接口，直接改 base_url 即可。

### 备选轻量方案
如果上述生态对你过重，可以考虑 **`markusbegerow/local-llm-odoo`**（MIT 许可）：Odoo 18 的本地 LLM 集成，通过 Ollama、LM Studio 或任何 OpenAI 兼容 API 在 Odoo 中直接对话[[1]](https://github.com/markusbegerow/local-llm-odoo)，包含一个可嵌入任意 Odoo 视图的聊天 widget[[1]](https://github.com/markusbegerow/local-llm-odoo)。

> ⚠️ 注意事项：第三方模块可能滞后于 Odoo 版本升级，为 v16 构建的模块不一定能在 v18 上直接工作[[8]](https://oec.sh/guides/odoo-ai-community)，建议在测试库先验证版本兼容性。此外，OCA 正在推进自己的 LLM 集成方案[[1]](https://github.com/orgs/OCA/discussions/201)，可以持续关注。

## 三、本地模型服务部署建议

| 推理后端 | 适用场景 | 优劣 |
|---------|---------|------|
| **Ollama** | 个人/小团队，快速原型 | 部署一键化、模型管理方便；吞吐和并发较弱 |
| **vLLM** | 生产环境、高并发 | 吞吐最高、支持 Continuous Batching；配置稍复杂 |
| **Xinference** | 需要同时跑 LLM+Embedding+Rerank | 一站式、OpenAI 兼容；国内社区活跃，对 Qwen/GLM 支持友好 |
| **FastChat** | 学术/测试 | 灵活但维护不如前三者活跃 |

**推荐组合**：
- LLM：`Qwen2.5-14B-Instruct` 或 `GLM-4-9B-Chat`（用 vLLM 部署）
- Embedding：`bge-m3` 或 `bge-large-zh-v1.5`（中文效果好）
- Rerank：`bge-reranker-v2-m3`（RAG 召回后做精排）

启动 vLLM 示例：
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-14B-Instruct \
  --served-model-name qwen2.5-14b \
  --host 0.0.0.0 --port 8000 \
  --gpu-memory-utilization 0.9
```
然后在 Odoo 的 LLM Provider 配置中填入 `http://<ip>:8000/v1` 即可。

## 四、实施步骤

**第 1 步：基础环境**
1. 用 vLLM 或 Xinference 部署 Qwen/GLM，暴露 OpenAI 兼容接口；再单独跑一个 Embedding 模型（bge-m3）。
2. 验证接口：`curl http://localhost:8000/v1/chat/completions ...` 能返回即可。

**第 2 步：安装 Odoo 模块**

将以下模块放入 `addons` 目录（从 apexive 的 GitHub 仓库克隆）：
```bash
git clone https://github.com/apexive/odoo-llm /path/to/addons/odoo-llm
pip install requests cryptography tiktoken pgvector  # 根据各模块 requirements
```
然后执行：
```bash
./odoo-bin -d yourdb -i llm,llm_thread,llm_assistant,llm_knowledge,llm_tool,llm_openai_compatible --stop-after-init
```

**第 3 步：在 Odoo 内配置**
1. `LLM → Configuration → Providers`，新建 Provider，选择 "OpenAI Compatible"，base_url 填本地 vLLM 地址，API key 随便填一个（vLLM 默认不校验）。
2. 点击 "Fetch Models" 拉取模型列表（类似 点击 Fetch Models 使用 API key 导入可用的 AI 模型[[4]](https://apps.odoo.com/apps/modules/18.0/llm_thread)）。
3. 新建 Assistant，设置系统 prompt（例如"你是 XX 公司的 Odoo 助手…"），绑定模型。
4. 在 Knowledge 模块上传 PDF / 导入 Odoo 文档记录，触发 embedding 入库。

**第 4 步：验证**
- 打开 Discuss 旁边的 AI Chat 面板，发起对话；
- 测试 RAG：上传一份内部制度 PDF，问一个只有里面才有答案的问题；
- 测试工具调用：让助手"创建一个销售订单给客户 ABC"。

## 五、进一步开发指南

### 1. 自定义业务工具（Tool Calling）
让 AI 能操作你的业务模型。创建自定义模块，示例：

```python
# your_module/models/sale_tools.py
from odoo import models
from odoo.addons.llm_tool.tools import llm_tool  # 装饰器

class SaleOrderTool(models.Model):
    _inherit = 'sale.order'

    @llm_tool(
        description="查询指定客户最近 N 条销售订单",
        parameters={
            "partner_name": {"type": "string", "description": "客户名称"},
            "limit": {"type": "integer", "default": 5}
        }
    )
    @api.model
    def llm_query_recent_orders(self, partner_name, limit=5):
        partner = self.env['res.partner'].search([('name', 'ilike', partner_name)], limit=1)
        if not partner:
            return {"error": "客户不存在"}
        orders = self.search([('partner_id', '=', partner.id)], limit=limit, order='date_order desc')
        return [{"name": o.name, "amount": o.amount_total, "state": o.state} for o in orders]
```

### 2. 自动总结指令（Chatter 摘要 / 邮件摘要）
在 `mail.thread` 上做扩展，加一个 "AI 总结" 按钮：

```python
class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def action_ai_summarize(self):
        messages = self.message_ids.sorted('date').mapped('body')
        text = "\n".join(self.env['ir.qweb']._html2text(m) for m in messages)
        provider = self.env['llm.provider'].search([('default', '=', True)], limit=1)
        summary = provider.chat_completion(
            model='qwen2.5-14b',
            messages=[
                {"role": "system", "content": "用 3-5 句话中文总结以下对话的要点和待办。"},
                {"role": "user", "content": text}
            ]
        )
        self.message_post(body=f"<b>AI 摘要：</b><br/>{summary}")
```
注册一个按钮到 form view header 即可在任意记录（CRM 商机、项目任务、工单…）上使用。

### 3. 知识库扩展策略
- **数据源**：除上传 PDF 外，可以写一个 cron，把 Odoo 内的 `knowledge.article`（如装了）、`product.template.description`、`helpdesk.ticket` 等记录自动 embedding 入库；
- **切片**：对中文语料，建议按标点+滑动窗口切，chunk 500–800 字符、overlap 100；
- **Rerank**：召回 top-20，再用 bge-reranker 精排到 top-5 传给 LLM，精度提升显著；
- **Citations**：把检索到的 chunk 原文作为上下文，并在 prompt 中要求 LLM "必须引用 [doc_id] 作为来源"。

### 4. Qwen / GLM 的特别优化
- **System Prompt 中文化**：模板里明确中文输出、禁止代码混英；
- **Function Calling 兼容性**：Qwen2.5 原生支持 OpenAI 函数调用格式；GLM-4 需要用 `glm-4-9b-chat` 以上版本，某些旧版 chatglm3 需要走 `tools` 字段适配；
- **上下文长度**：Qwen2.5-14B 支持 128K，做长文档总结很合适；GLM-4-9B 默认 128K；
- **温度**：总结类任务建议 `temperature=0.2, top_p=0.8`。

### 5. 权限与安全
- 为 LLM Provider、Assistant、Knowledge Collection 设置 `ir.model.access` 和 record rules，避免普通用户看到敏感配置；
- 所有出入站日志落库到 `llm.message`，方便审计；
- 加密 key 建议从环境变量读取而不是存在 System Parameters 里[[1]](https://github.com/markusbegerow/local-llm-odoo)。

### 6. 进阶：Agent / MCP
如果要让 AI 跨模块"做事"（例如"帮我找出逾期应收并发催款邮件"），可以关注：
- **`llm_letta`**：与 MemGPT / Letta 框架的集成[[1]](https://github.com/orgs/OCA/discussions/201)，用于长记忆 agent；
- **OCA 的 LLM agent 方向**：把推理/agent 模型连接到 Odoo，通过函数进行检索、通过 server action 进行数据库操作[[1]](https://github.com/orgs/OCA/discussions/201)。
- 自建 **MCP Server** 把 Odoo 暴露给 Claude Desktop / Cursor / n8n 等客户端。

## 六、落地路线图（建议）

| 阶段 | 目标 | 周期 |
|------|------|------|
| Phase 1 | vLLM + Qwen2.5 跑通；安装 llm + llm_thread + llm_openai_compatible；Discuss 里能对话 | 1–2 天 |
| Phase 2 | 接入 llm_knowledge + bge-m3；导入公司文档，跑通 RAG 问答 | 3–5 天 |
| Phase 3 | 开发 2–3 个业务 Tool（销售查询、库存查询、工单摘要）；在 CRM/Helpdesk 上加 "AI 总结" 按钮 | 1–2 周 |
| Phase 4 | 权限、日志审计、Rerank、Prompt 调优；多助手角色；准入测试 | 1–2 周 |
| Phase 5 | Agent 化（Letta / MCP），打通工作流自动化 | 按需 |

---

如果你告诉我具体的硬件（几张卡、显存）、使用场景（CRM/制造/电商？）和用户规模，我可以进一步帮你细化模型选型（Qwen 还是 GLM、几B参数、是否量化）以及 Prompt 模板和 RAG 参数。

---
Learn more:
1. [GitHub - markusbegerow/local-llm-odoo: Local LLM integration for Odoo 18 - chat with AI directly in Odoo using Ollama, LM Studio, or any OpenAI-compatible API.](https://github.com/markusbegerow/local-llm-odoo)
2. [HELP WANTED: Odoo LLM agents are here! · OCA · Discussion #201](https://github.com/orgs/OCA/discussions/201)
3. [Ollama LLM Integration | Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/llm_ollama)
4. [Odoo Community Association · GitHub](https://github.com/oca)
5. [LLM Integration Base | Odoo Apps Store](https://apps.odoo.com/apps/modules/16.0/llm)
6. [Odoo ChatGPT Integration | Odoo Apps Store](https://apps.odoo.com/apps/modules/16.0/is_chatgpt_integration)
7. [Easy AI Chat | Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/llm_thread)
8. [GitHub - thespino/odoogpt: Integrate Odoo with OpenAI and GPT Models. Make OdooBot finally useful by integrating with OpenAI ChatGPT-3! · GitHub](https://github.com/thespino/odoogpt)
9. [Mistral AI LLM Integration | Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/llm_mistral)
10. [Odoo AI Chatbot | AIAgent | Odoo Smart Assistant | AskOdoo | Copilot AI | ChatGPT for Odoo | Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/odoo_ai_chatbot)
11. [local\_llm\_odoo | Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/local_llm_odoo)
12. [GitHub - OCA/OCB: Odoo Community Backports · GitHub](https://github.com/OCA/OCB)
13. [LLM ComfyUI Integration | Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/llm_comfyui)
14. [GitHub - OCA/web: Odoo web client UI related addons · GitHub](https://github.com/OCA/web)
15. [AI for Odoo Community Edition - Complete Guide (2026) | OEC.sh Guides](https://oec.sh/guides/odoo-ai-community)
16. [GitHub - machanic16/chatgpt-odoo: This module integrate the powerfull AI ChatGPT with the great ERP system Odoo](https://github.com/machanic16/chatgpt-odoo)
17. [wk\_ai\_opensource\_llm\_base | Odoo Apps Store](https://apps.odoo.com/apps/modules/17.0/wk_ai_opensource_llm_base)
18. [GitHub - OCA/project: Odoo Project Management and Services Company Addons · GitHub](https://github.com/OCA/project)
19. [Replicate LLM Integration | Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/llm_replicate)
20. [Github Connector - OCA extension | The Odoo Community Association | OCA](https://apps.odoo-community.org/shop/github-connector-oca-extension-3411)



*Thinking...*

> 
>